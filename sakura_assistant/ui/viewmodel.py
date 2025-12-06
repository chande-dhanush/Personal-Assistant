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
from ..core import tools
from ..memory.ingestion.pipeline import get_ingestion_pipeline
from ..utils.file_registry import get_file_registry

class ChatViewModel(QtCore.QObject):
    # Signals
    message_received = QtCore.pyqtSignal(str, str) # role, content
    status_changed = QtCore.pyqtSignal(str) # status text
    listening_state_changed = QtCore.pyqtSignal(bool) # is_listening
    error_occurred = QtCore.pyqtSignal(str) # error message
    file_list_updated = QtCore.pyqtSignal()
    ingestion_status_changed = QtCore.pyqtSignal(bool) # is_ingesting
    chat_cleared = QtCore.pyqtSignal()

    def __init__(self):
        super().__init__()
        self.thread_pool = QtCore.QThreadPool()
        self.conversation_history = []
        self.is_processing = False
        self.listening = False
        
        # Initialize systems
        self._init_memory()
        tools.state_manager._init_spotify()

    def _init_memory(self):
        """Initialize memory in background."""
        def _task():
            try:
                store = get_memory_store() # Triggers lazy load
                
                # Only load from store if local history is empty (fresh start)
                # If bubble.py passed history, we assume it's up to date.
                if not self.conversation_history:
                    self.conversation_history = store.conversation_history
                
                # If we have local history but store is empty (unlikely unless store failed load), 
                # we could push to store, but let's just leave it for auto-save.
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

    def send_message(self, text: str):
        """Handle user message submission."""
        if not text.strip() or self.is_processing:
            return

        self.is_processing = True
        
        # 1. Add to local history & memory
        # Note: add_message_to_memory updates the store, and self.conversation_history 
        # is a reference to store.conversation_history, so this updates both.
        add_message_to_memory(text, "user")
        self.message_received.emit("user", text)

        # 2. Start Agent Worker
        worker = AgentWorker(text, self.conversation_history)
        worker.signals.update_chat.connect(self._on_agent_update) # Partial updates if supported
        worker.signals.finished.connect(self._on_agent_finished)
        worker.signals.error.connect(self._on_agent_error)
        self.thread_pool.start(worker)

    def _on_agent_update(self):
        # Reload history if needed, or just signal refresh
        # For now, AgentWorker updates the history list in place (by reference) 
        # but we should probably be more explicit.
        # The current AgentWorker implementation appends to the passed list.
        pass

    def _on_agent_finished(self):
        self.is_processing = False
        # The last message in history is the assistant's response
        if self.conversation_history and self.conversation_history[-1]['role'] == 'assistant':
            last_msg = self.conversation_history[-1]['content']
            self.message_received.emit("assistant", last_msg)
        
        # Auto-save
        save_conversation_async(self.conversation_history)

    def _on_agent_error(self, err):
        self.is_processing = False
        self.error_occurred.emit(str(err))

    def start_listening(self):
        if self.listening: return
        self.listening = True
        self.listening_state_changed.emit(True)
        
        recognizer = sr.Recognizer()
        
        # Use configured microphone index if available
        from ..config import MICROPHONE_INDEX
        mic_idx = MICROPHONE_INDEX
        print(f"🎤 Starting Mic with Index: {mic_idx if mic_idx is not None else 'Default'}")
        
        microphone = sr.Microphone(device_index=mic_idx)
        worker = VoiceWorker(recognizer, microphone)
        
        worker.signals.result.connect(self._on_voice_result)
        worker.signals.finished.connect(self._on_voice_finished)
        self.thread_pool.start(worker)

    def stop_listening(self):
        self.listening = False
        self.listening_state_changed.emit(False)

    def _on_voice_result(self, text):
        self.stop_listening()
        self.send_message(text)

    def _on_voice_finished(self):
        if self.listening:
            self.stop_listening()

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
        self.conversation_history = []
        save_conversation_async([])
        clear_conversation_history()
        self.chat_cleared.emit()

    def get_files(self):
        try:
            return get_file_registry().list_files()
        except:
            return []
