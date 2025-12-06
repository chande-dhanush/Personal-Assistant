from PyQt5 import QtCore
import speech_recognition as sr
import traceback
from ..core.llm import run_agentic_response
from ..utils.tts import text_to_speech
from ..memory.faiss_store import add_message_to_memory, save_conversation
import sys

class WorkerSignals(QtCore.QObject):
    """
    Defines the signals available from a running worker thread.
    """
    finished = QtCore.pyqtSignal()
    error = QtCore.pyqtSignal(tuple)
    result = QtCore.pyqtSignal(object)
    progress = QtCore.pyqtSignal(int)
    
    # Specific signals for our app
    update_ui = QtCore.pyqtSignal(str) # For text updates
    update_chat = QtCore.pyqtSignal()  # To refresh chat area
    start_listening = QtCore.pyqtSignal() # To trigger listening again

class AgentWorker(QtCore.QRunnable):
    """
    Worker thread for running the Agent LLM response.
    """
    def __init__(self, user_message, history):
        super(AgentWorker, self).__init__()
        self.user_message = user_message
        self.history = history
        self.signals = WorkerSignals()

    @QtCore.pyqtSlot()
    def run(self):
        try:
            # 1. Get LLM Response
            response = run_agentic_response(self.user_message, self.history)
            
            # 2. Update Memory
            add_message_to_memory(response, "assistant")
            save_conversation(self.history)
            
            # 3. Update UI (via signal)
            self.signals.update_chat.emit()
            
            # 4. TTS (Blocking or Callback?)
            # We'll run TTS here. It might block this worker thread, which is fine for QThreadPool.
            # But we need to know when it's done to trigger listening.
            
            # 4. TTS
            # We run TTS here. Since auto-listening is disabled, we don't need a callback.
            text_to_speech(response)
            
        except Exception:
            traceback.print_exc()
            exctype, value = sys.exc_info()[:2]
            self.signals.error.emit((exctype, value, traceback.format_exc()))
        finally:
            self.signals.finished.emit()

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
            self.signals.finished.emit()
