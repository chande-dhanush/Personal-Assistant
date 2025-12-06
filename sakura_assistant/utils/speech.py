import os
import threading
from typing import Optional

try:
    from faster_whisper import WhisperModel
    WHISPER_AVAILABLE = True
except ImportError:
    WHISPER_AVAILABLE = False
    print("⚠️ faster-whisper not installed. Voice input will be disabled.")

class LocalSpeechEngine:
    _instance = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(LocalSpeechEngine, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
            
        self.model = None
        self.model_size = "tiny.en" # Optimized for speed on small PC
        self.device = "cpu" # Default to CPU for compatibility
        self.compute_type = "int8" # Quantization for speed
        
        self._initialized = True

    def preload_model(self):
        """Lazy load the model in a background thread if not already loaded."""
        if not WHISPER_AVAILABLE or self.model:
            return

        print(f"🎙️ Loading Local Whisper ({self.model_size})...")
        try:
            # Run on CPU with INT8 for maximum compatibility/speed on low-end PCs
            self.model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
            print("✅ Local Whisper Loaded.")
        except Exception as e:
            print(f"❌ Failed to load Whisper: {e}")

    def transcribe(self, audio_data) -> str:
        """
        Transcribe audio data (file path or bytes).
        For now, we expect a file path or a binary stream compatible with faster-whisper.
        """
        if not WHISPER_AVAILABLE:
            return ""
            
        if not self.model:
            self.preload_model()
            
        if not self.model:
            return ""

        try:
            segments, info = self.model.transcribe(audio_data, beam_size=5)
            text = " ".join([segment.text for segment in segments])
            return text.strip()
        except Exception as e:
            print(f"❌ Transcription failed: {e}")
            return ""

# Global Accessor
_speech_engine = None

def get_speech_engine():
    global _speech_engine
    if not _speech_engine:
        _speech_engine = LocalSpeechEngine()
    return _speech_engine
