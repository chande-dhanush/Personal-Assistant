from PyQt5 import QtCore
import speech_recognition as sr
import traceback
from ..core.llm import run_agentic_response
from ..utils.tts import text_to_speech
from ..utils.memory_judger import should_store_message
from ..memory.faiss_store import add_message_to_memory
from ..utils.stability_logger import log_flow, log_success, log_error
import sys

class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.
    V3: Only 'finished' carries the result payload dict.
    """
    finished = QtCore.pyqtSignal(object) # Carries result payload (dict)
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)
    
    # Voice-specific
    start_listening = QtCore.pyqtSignal()


class AgentWorker(QtCore.QRunnable):
    """
    Worker thread for running the Agent LLM response.
    V3: Emits finished(dict) with full payload.
    """
    def __init__(self, user_message, history):
        super(AgentWorker, self).__init__()
        self.user_message = user_message
        self.history = history
        self.signals = WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self):
        payload = None
        had_error = False
        
        try:
            log_flow("ViewModel → Worker", f"history_len={len(self.history)}")
            # 1. Get LLM Response
            result_obj = run_agentic_response(self.user_message, self.history)
            
            # Ensure dict structure with role
            if isinstance(result_obj, dict):
                response_text = result_obj.get("content", "")
                metadata = result_obj.get("metadata", {})
            else:
                response_text = str(result_obj)
                metadata = {"mode": "Legacy", "confidence": 0.0, "tool_used": "None"}
            
            # Build V3 Payload
            payload = {
                "role": "assistant",
                "content": response_text,
                "metadata": metadata
            }
            
            # 2. ALWAYS append to conversation history first (critical fix)
            from ..memory.faiss_store import get_memory_store
            store = get_memory_store()
            store.append_to_history({"role": "assistant", "content": response_text})
            
            # 3. Use Memory Judger to decide if response should be stored in FAISS
            should_store, reason, importance = should_store_message(response_text, "assistant")
            
            if should_store:
                add_message_to_memory(response_text, "assistant")
            else:
                print(f"⏭️ Skipped FAISS: {reason}")
            
            # Note: save_conversation is handled by debounced store.request_save()
            # Do NOT call save here to avoid duplicate saves
            
            # 4. TTS
            text_to_speech(response_text)
            
            # 5. Log success
            log_flow("Worker → LLM → Worker", f"response_len={len(response_text)}")
            log_success()
            
        except Exception as e:
            had_error = True
            log_error(f"AgentWorker exception: {e}")
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            try:
                self.signals.error.emit((exctype, value, traceback.format_exc()))
            except Exception:
                pass
        
        finally:
            # CRITICAL: ALWAYS emit finished signal to unblock is_processing
            try:
                if payload is None:
                    payload = {
                        "role": "assistant",
                        "content": "I encountered an error processing your request.",
                        "metadata": {"mode": "Error", "confidence": 0.0}
                    }
                self.signals.finished.emit(payload)
            except Exception:
                pass


class VoiceWorker(QtCore.QRunnable):
    """
    Worker thread for handling Voice Input.
    """
    def __init__(self, recognizer, microphone):
        super(VoiceWorker, self).__init__()
        self.recognizer = recognizer
        self.microphone = microphone
        self.signals = WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self):
        temp_wav = f"temp_voice_{id(self)}.wav"
        try:
            # Adjust for ambient noise
            with self.microphone as source:
                self.recognizer.adjust_for_ambient_noise(source, duration=0.5)
                self.recognizer.energy_threshold = max(100, self.recognizer.energy_threshold)
                self.recognizer.pause_threshold = 1.0 
                
                print("🎙️ Listening...")
                # Listen (timeout=None means wait forever until speech starts)
                audio = self.recognizer.listen(source, timeout=None, phrase_time_limit=15)
                
                # Transcribe with Google (Fast, Online)
                try:
                    text = self.recognizer.recognize_google(audio)
                    print(f"✅ [Voice]: {text}")
                    if text:
                        self.signals.result.emit(text)
                except sr.UnknownValueError:
                    pass # Silence/Background noise
                except sr.RequestError as e:
                    print(f"❌ Google API Error: {e}")
                    self.signals.result.emit(f"Error: {e}")
                except Exception as e:
                    print(f"❌ Voice Error: {e}")
                
        except sr.WaitTimeoutError:
            pass
        except Exception as e:
            print(f"⚠️ Voice Worker Error: {e}")
            # traceback.print_exc()
        finally:
            # Cleanup
            import os
            if os.path.exists(temp_wav):
                try: os.remove(temp_wav)
                except: pass
            self.signals.finished.emit(None)  # V3: Signal expects object, pass None for voice-only
