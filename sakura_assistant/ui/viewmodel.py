from PyQt5 import QtCore
import threading
import speech_recognition as sr
from .workers import AgentWorker, VoiceWorker
from ..memory.faiss_store import (
    get_memory_store, 
    add_message_to_memory, 
    save_conversation_async, 
    clear_conversation_history,
    get_memory_stats
)
from ..utils.memory_judger import should_store_message
from ..core import tools
from ..memory.ingestion.pipeline import get_ingestion_pipeline
from ..utils.file_registry import get_file_registry
from ..config import get_note_root
from ..utils.stability_logger import log_flow, log_mem
import os

from enum import Enum, auto


class InteractionMode(Enum):
    """Global interaction mode - single source of truth for wake/mic state."""
    IDLE = auto()           # Wake word active, ready to detect
    WAKE_HANDOFF = auto()   # "Yes?" TTS playing after wake detection
    VOICE_WAKE = auto()     # Listening after wake word
    VOICE_MANUAL = auto()   # Listening after manual mic button
    RESPONDING = auto()     # LLM processing response


class ChatViewModel(QtCore.QObject):
    # Signals
    # V3 Unified Signal: All messages (user/bot/system) flow here as dicts
    response_ready = QtCore.pyqtSignal(dict) 
    
    status_changed = QtCore.pyqtSignal(str) # status text
    listening_state_changed = QtCore.pyqtSignal(bool) # is_listening
    error_occurred = QtCore.pyqtSignal(str) # error message
    file_list_updated = QtCore.pyqtSignal()
    ingestion_status_changed = QtCore.pyqtSignal(bool) # is_ingesting
    chat_cleared = QtCore.pyqtSignal()
    notes_list_updated = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.thread_pool = QtCore.QThreadPool()
        self.conversation_history = []
        self._history_lock = threading.Lock()  # Patch 3: Thread safety for history
        self.is_processing = False
        self.listening = False
        self._typing = False  # Track if user is typing (for wake word pause)
        
        # V4.2: Global interaction mode - single authority for wake/mic control
        self._interaction_mode = InteractionMode.IDLE
        
        # Initialize systems
        self._init_memory()
        tools.state_manager._init_spotify()
        
        # Initialize Scheduler (Agentic Background Tasks)
        from ..core.scheduler import AgentScheduler
        self.scheduler = AgentScheduler()
        self.scheduler.alert_triggered.connect(self._on_scheduler_alert)
        self.scheduler.start()
        
        # V4: Initialize Wake Word Detection (if enabled)
        self._init_wake_word()
    
    def _set_mode(self, new_mode: InteractionMode):
        """Set interaction mode and control wake word accordingly."""
        old_mode = self._interaction_mode
        self._interaction_mode = new_mode
        print(f"[MODE] {old_mode.name} → {new_mode.name}")
        
        # Control wake word based on mode
        if new_mode == InteractionMode.IDLE:
            self._resume_wake_word()
        else:
            self._pause_wake_word()
    
    def _pause_wake_word(self):
        """Pause wake word detection."""
        try:
            from ..utils.wake_word import pause_wake_detection
            pause_wake_detection()
        except:
            pass
    
    def _resume_wake_word(self):
        """Resume wake word detection."""
        try:
            from ..utils.wake_word import resume_wake_detection
            resume_wake_detection()
        except:
            pass

    def _init_memory(self):
        """Initialize memory in background."""
        def _task():
            try:
                store = get_memory_store() # Triggers lazy load
                
                # ALWAYS point to store's list at boot (critical for shared reference)
                self.conversation_history = store.conversation_history
                
                # Emit initial stats
                stats = get_memory_stats()
                self._emit_memory_stats(stats)
            except Exception as e:
                self.error_occurred.emit(f"Memory Init Error: {e}")
        
        threading.Thread(target=_task, daemon=True).start()

    def _emit_memory_stats(self, stats):
        if stats and "error" not in stats:
            total = stats.get("total_memories", 0)
            health = stats.get("system_health", "unknown")
            self.status_changed.emit(f"🧠 Memory: {total} stored | Status: {health}")
    
    def _init_wake_word(self):
        """Initialize wake word detection if enabled."""
        from ..config import ENABLE_WAKE_WORD, WAKE_WORD_THRESHOLD
        
        if not ENABLE_WAKE_WORD:
            return
        
        try:
            from ..utils.wake_word import init_wake_detector, get_template_count
            
            count = get_template_count()
            if count == 0:
                return
            
            detector = init_wake_detector(
                on_wake_detected=self._on_wake_detected,
                threshold=WAKE_WORD_THRESHOLD
            )
            
            if detector and detector.start():
                print(f"🎤 Wake word active ({count} templates)")
        except Exception as e:
            print(f"⚠️ Wake word init failed: {e}")
    
    def _on_wake_detected(self):
        """Handle wake word detection - only if in IDLE mode."""
        # V4.2: Mode guard - wake word can ONLY trigger when IDLE
        if self._interaction_mode != InteractionMode.IDLE:
            print(f"[WAKE] Ignored - mode is {self._interaction_mode.name}")
            return
        
        log_flow("WakeWord", "DETECTED")
        
        # Transition: IDLE → WAKE_HANDOFF
        self._set_mode(InteractionMode.WAKE_HANDOFF)
        
        # Stop any playing TTS
        try:
            from ..utils.tts import stop_speaking
            stop_speaking()
        except:
            pass
        
        # Speak "Yes?" via Kokoro TTS with callback
        try:
            from ..utils.tts import text_to_speech
            text_to_speech("Yes?", callback=self._on_wake_tts_done)
        except Exception as e:
            log_flow("WakeWord", f"TTS failed: {e}")
            self._on_wake_tts_done()
    
    def _on_wake_tts_done(self):
        """After 'Yes?' TTS finishes, start voice recognition."""
        # V4.2: Only proceed if we're in WAKE_HANDOFF mode
        if self._interaction_mode != InteractionMode.WAKE_HANDOFF:
            self._set_mode(InteractionMode.IDLE)
            return
        
        # Transition: WAKE_HANDOFF → VOICE_WAKE
        self._set_mode(InteractionMode.VOICE_WAKE)
        self._start_voice_recognition()
    
    def _start_voice_recognition(self):
        """Start voice recognition - unified handler for wake and manual modes."""
        if self.listening:
            return  # Already listening
        
        self.listening = True
        self.listening_state_changed.emit(True)
        
        # Create and run VoiceWorker
        from .workers import VoiceWorker
        import speech_recognition as sr
        
        recognizer = sr.Recognizer()
        
        # Use MICROPHONE_INDEX from config if available
        try:
            from ..config import MICROPHONE_INDEX
            mic_index = int(MICROPHONE_INDEX) if MICROPHONE_INDEX else None
        except:
            mic_index = None
        
        microphone = sr.Microphone(device_index=mic_index)
        
        worker = VoiceWorker(recognizer, microphone)
        worker.signals.result.connect(self._on_voice_result)
        worker.signals.finished.connect(self._on_voice_finished)
        
        self.thread_pool.start(worker)
    
    def _on_voice_result(self, text):
        """Handle voice recognition result (for both wake and manual modes)."""
        print(f"🎧 Voice result: {text}")
        if text and not text.startswith("Error:"):
            # Transition to RESPONDING mode
            self._set_mode(InteractionMode.RESPONDING)
            # Send through normal message flow
            self.send_message(text)
    
    def _on_voice_finished(self, _):
        """Voice recognition finished - return to IDLE mode."""
        self.listening = False
        self.listening_state_changed.emit(False)
        
        # If still in a voice mode, transition back to IDLE
        if self._interaction_mode in (InteractionMode.VOICE_WAKE, InteractionMode.VOICE_MANUAL):
            self._set_mode(InteractionMode.IDLE)
    
    # Patch 3: Thread-safe history helpers
    def append_to_history(self, msg: dict):
        """Thread-safe append using Store's method (ensures persistence)."""
        get_memory_store().append_to_history(msg)
    
    def get_history_snapshot(self) -> list:
        """Get snapshot from Store to ensure consistency."""
        return list(get_memory_store().conversation_history)

    def send_message(self, text: str):
        """Handle user message submission."""
        if not text.strip():
            return
        
        # V4: Stop any playing TTS when user sends message
        # "If user acts, assistant shuts up"
        try:
            from ..utils.tts import stop_speaking
            stop_speaking()
        except Exception:
            pass
        
        # Defensive reset if stuck processing
        if self.is_processing:
            self.is_processing = False
        
        log_flow("USER → ViewModel", f"msg_len={len(text)}")
        self.is_processing = True
        
        # V4: Update user state on each message (lazy reset, no timers)
        from ..utils.user_state import update_user_state
        current_state = update_user_state(text, is_voice=False)
        log_flow("UserState", f"state={current_state}")
        
        # V4: Check for routine trigger BEFORE agent processing
        # Routines emit directly, bypass LLM pipeline
        from ..core.routines import get_routine_message_if_triggered
        routine_msg = get_routine_message_if_triggered()
        if routine_msg:
            self.response_ready.emit(routine_msg)
            # Add to history
            store = get_memory_store()
            store.append_to_history({"role": "assistant", "content": routine_msg["content"]})
            log_flow("ROUTINE", "Emitted directly without LLM")
        
        # 1. ALWAYS append to conversation history first (critical fix)
        store = get_memory_store()
        store.append_to_history({"role": "user", "content": text})
        
        # 2. Use Memory Judger to decide if user message should be stored in FAISS
        should_store, reason, importance = should_store_message(text, "user")
        if should_store:
            add_message_to_memory(text, "user")
        else:
            print(f"⏭️ User msg skipped FAISS: {reason}")
        
        # Emit UNIFIED Dict for User (UI display)
        self.response_ready.emit({
            "role": "user",
            "content": text,
            "metadata": {}
        })

        # 3. Start Agent Worker
        worker = AgentWorker(text, self.conversation_history)
        worker.signals.finished.connect(self._on_agent_finished)
        worker.signals.error.connect(self._on_agent_error)
        self.thread_pool.start(worker)

    def _on_agent_update(self):
        pass

    def _on_agent_finished(self, result_payload=None):
        log_flow("LLM → ViewModel", f"payload_type={type(result_payload).__name__}")
        self.is_processing = False
        
        # V4.3: Return to IDLE mode (triggers wake word resume)
        self._set_mode(InteractionMode.IDLE)
        
        # Ensure we have payload logic
        # If payload is missing (shouldn't happen with new worker), construct backup
        final_payload = result_payload
        
        if not final_payload or not isinstance(final_payload, dict):
            # Fallback (Legacy Worker or logic error)
             if self.conversation_history and self.conversation_history[-1]['role'] == 'assistant':
                 content = self.conversation_history[-1]['content']
             else:
                 content = "" # Error state
                 
             final_payload = {
                 "role": "assistant",
                 "content": content,
                 "metadata": {"mode": "Rescue", "confidence": 0.0}
             }

        # Role safety
        if "role" not in final_payload:
            final_payload["role"] = "assistant"

        self.response_ready.emit(final_payload)
        
        # NOTE: conversation_history is ALREADY updated by add_message_to_memory() calls
        # (in send_message for user, in workers.py for assistant)
        # since self.conversation_history shares the same reference as store.conversation_history.
        # We ONLY need to persist it here. DO NOT APPEND AGAIN (causes duplicates).
        
        # Auto-save to persist
        save_conversation_async(self.conversation_history)

    def _on_agent_error(self, err):
        self.is_processing = False
        # V4.3: Return to IDLE mode (triggers wake word resume)
        self._set_mode(InteractionMode.IDLE)
        self.error_occurred.emit(str(err))

    def start_listening(self):
        """Manual mic button - uses VOICE_MANUAL mode (no 'Yes?')."""
        if self.listening: return
        
        # V4.2: Set VOICE_MANUAL mode - this pauses wake word
        self._set_mode(InteractionMode.VOICE_MANUAL)
        
        self.listening = True
        self.listening_state_changed.emit(True)
        
        recognizer = sr.Recognizer()
        
        # Use configured microphone index if available
        from ..config import MICROPHONE_INDEX
        mic_idx = MICROPHONE_INDEX
        
        microphone = sr.Microphone(device_index=mic_idx)
        worker = VoiceWorker(recognizer, microphone)
        
        # Use unified handlers
        worker.signals.result.connect(self._on_voice_result)
        worker.signals.finished.connect(self._on_voice_finished)
        self.thread_pool.start(worker)

    def stop_listening(self):
        """Stop voice recognition."""
        self.listening = False
        self.listening_state_changed.emit(False)
        # Mode transition handled by _on_voice_finished

    def toggle_listening(self):
        if self.listening:
            self.stop_listening()
        else:
            self.start_listening()

    def ingest_file(self, file_path):
        self.status_changed.emit("⏳ Ingesting file...")
        self.ingestion_status_changed.emit(True)
        
        def _task():
            try:
                pipeline = get_ingestion_pipeline()
                result = pipeline.ingest_file_sync(file_path)
                self.ingestion_status_changed.emit(False)
                
                if isinstance(result, dict) and not result.get("error"):
                    self.status_changed.emit("✅ Ingestion complete.")
                    self.file_list_updated.emit()
                else:
                    msg = result.get("message") if isinstance(result, dict) else str(result)
                    self.error_occurred.emit(f"Ingest Error: {msg}")
            except Exception as e:
                self.ingestion_status_changed.emit(False)
                self.error_occurred.emit(f"Ingest Failed: {e}")

        threading.Thread(target=_task, daemon=True).start()

    def delete_file(self, file_id):
        try:
            registry = get_file_registry()
            registry.delete_file(file_id)
            self.file_list_updated.emit()
            self.status_changed.emit("🗑️ File deleted.")
        except Exception as e:
            self.error_occurred.emit(f"Delete Error: {e}")

    def clear_history(self):
        # Fix: Use store clear method to maintain shared reference
        store = get_memory_store()
        store.clear_all_memory()
        # self.conversation_history is shared ref, so it should be cleared by store
        # But safest to force clear the object reference held by store if possible
        # store.clear_all_memory already does self.conversation_history.clear()
        
        save_conversation_async([])
        self.chat_cleared.emit()

    def get_files(self):
        try:
            return get_file_registry().list_files()
        except:
            return []

    def _on_scheduler_alert(self, message: str):
        """Handle alerts from background scheduler."""
        # 1. Show status
        self.status_changed.emit(f"🔔 {message}")
        
        # 2. Speak/Display as Assistant Message
        # We assume this is an interrupt, so we just push it to the chat
        self.response_ready.emit({
            "role": "assistant",
            "content": message,
            "metadata": {"mode": "Alert", "confidence": 1.0}
        })
        
        # 3. Add to memory
        # 3. Add to memory via Store
        self.append_to_history({"role": "assistant", "content": message})
        # Note: append_to_history automatically saves metadata

    def delete_message(self, content, role, delete_from_memory=False, save_immediate=True):
        """Delete a message from history."""
        target_idx = -1
        for i, msg in enumerate(self.conversation_history):
            if msg.get('content') == content and msg.get('role') == role:
                target_idx = i
                break 
        
        if target_idx != -1:
            self.conversation_history.pop(target_idx)
            if delete_from_memory and save_immediate:
                save_conversation_async(self.conversation_history)
            
    def force_save_history(self):
        save_conversation_async(self.conversation_history)

    def get_notes(self):
        """Scan NOTE_ROOT for .md files."""
        root = get_note_root()
        all_notes = []
        try:
            for dirpath, dirnames, filenames in os.walk(root):
                folder = os.path.relpath(dirpath, root)
                if folder == ".": folder = "Root"
                
                for f in filenames:
                    if f.endswith(".md"):
                        all_notes.append({
                            "title": f,
                            "folder": folder,
                            "path": os.path.join(dirpath, f)
                        })
        except Exception as e:
            print(f"Notes Scan Error: {e}")
            
        return all_notes

    def read_note_to_chat(self, path):
        """Read a note and send as assistant message (for preview)."""
        try:
            with open(path, 'r', encoding='utf-8') as f:
                content = f.read()
            # Send to UI as dict
            preview = f"📜 **Note Content** ({os.path.basename(path)}):\n\n{content}"
            self.response_ready.emit({
                 "role": "assistant",
                 "content": preview,
                 "metadata": {"mode": "Reader", "confidence": 1.0}
            })
        except Exception as e:
            self.error_occurred.emit(f"Read Error: {e}")
