"""
Shared Microphone Stream - Single Owner Architecture

DESIGN:
- ONE mic stream for the entire application
- Frame fan-out to multiple consumers via callbacks
- Priority-based access control

PRIORITY ORDER (highest first):
1. Wake Word Recording (exclusive mode)
2. Voice Recognition (temporary exclusive)
3. Wake Word Detection (always-on when idle)

USAGE:
- All mic consumers register callbacks
- No component opens mic directly
"""

import threading
import time
import numpy as np
from typing import Callable, Optional, List
from collections import deque

# Lazy import
_pyaudio_available = None

def _check_pyaudio():
    global _pyaudio_available
    if _pyaudio_available is None:
        try:
            import pyaudio
            _pyaudio_available = True
        except ImportError:
            _pyaudio_available = False
    return _pyaudio_available


# Mic Configuration
SAMPLE_RATE = 16000          # 16kHz for speech recognition compatibility
CHUNK_SIZE = 1024            # ~64ms chunks
CHANNELS = 1
FORMAT_BITS = 16

# Singleton state
_stream = None
_audio = None
_running = False
_lock = threading.Lock()
_consumers: List[dict] = []  # {"name": str, "callback": Callable, "priority": int, "active": bool}


class MicStreamManager:
    """
    Singleton manager for shared microphone access.
    """
    
    @staticmethod
    def start():
        """Start the shared mic stream."""
        global _stream, _audio, _running
        
        if not _check_pyaudio():
            print("❌ Shared Mic: PyAudio not available")
            return False
        
        with _lock:
            if _running:
                return True
            
            try:
                import pyaudio
                _audio = pyaudio.PyAudio()
                
                # Find default input device
                device_index = None
                try:
                    from ..config import MICROPHONE_INDEX
                    if MICROPHONE_INDEX:
                        device_index = int(MICROPHONE_INDEX)
                except:
                    pass
                
                _stream = _audio.open(
                    format=pyaudio.paInt16,
                    channels=CHANNELS,
                    rate=SAMPLE_RATE,
                    input=True,
                    input_device_index=device_index,
                    frames_per_buffer=CHUNK_SIZE
                )
                
                _running = True
                
                # Start frame dispatch thread
                threading.Thread(target=MicStreamManager._frame_loop, daemon=True).start()
                
                print(f"🎤 Shared Mic: Started (rate={SAMPLE_RATE}, chunk={CHUNK_SIZE})")
                return True
                
            except Exception as e:
                print(f"❌ Shared Mic: Failed to start - {e}")
                return False
    
    @staticmethod
    def stop():
        """Stop the shared mic stream."""
        global _stream, _audio, _running
        
        with _lock:
            _running = False
            
            if _stream:
                try:
                    _stream.stop_stream()
                    _stream.close()
                except:
                    pass
                _stream = None
            
            if _audio:
                try:
                    _audio.terminate()
                except:
                    pass
                _audio = None
            
            print("🎤 Shared Mic: Stopped")
    
    @staticmethod
    def _frame_loop():
        """Main frame dispatch loop - reads mic and fans out to consumers."""
        global _running, _stream
        
        while _running:
            try:
                if _stream is None:
                    time.sleep(0.1)
                    continue
                
                # Read audio chunk
                data = _stream.read(CHUNK_SIZE, exception_on_overflow=False)
                
                # Convert to numpy array (normalized float32)
                samples = np.frombuffer(data, dtype=np.int16).astype(np.float32) / 32768.0
                
                # Fan out to active consumers (sorted by priority, highest first)
                with _lock:
                    active_consumers = [c for c in _consumers if c["active"]]
                    active_consumers.sort(key=lambda x: x["priority"], reverse=True)
                
                for consumer in active_consumers:
                    try:
                        # If exclusive consumer, only feed that one
                        if consumer.get("exclusive"):
                            consumer["callback"](samples, data)
                            break
                        else:
                            consumer["callback"](samples, data)
                    except Exception as e:
                        print(f"⚠️ Mic consumer '{consumer['name']}' error: {e}")
                
            except Exception as e:
                print(f"⚠️ Shared Mic frame error: {e}")
                time.sleep(0.1)
    
    @staticmethod
    def register_consumer(name: str, callback: Callable, priority: int = 0) -> str:
        """
        Register a mic frame consumer.
        
        Args:
            name: Consumer name (for logging)
            callback: Function(samples: np.ndarray, raw_bytes: bytes)
            priority: Higher = processed first (3=recording, 2=voice, 1=wake)
            
        Returns:
            Consumer ID
        """
        consumer_id = f"{name}_{id(callback)}"
        
        with _lock:
            _consumers.append({
                "id": consumer_id,
                "name": name,
                "callback": callback,
                "priority": priority,
                "active": False,
                "exclusive": False
            })
        
        print(f"🎤 Shared Mic: Registered consumer '{name}' (priority={priority})")
        return consumer_id
    
    @staticmethod
    def activate_consumer(consumer_id: str, exclusive: bool = False):
        """Activate a consumer to receive frames."""
        with _lock:
            for c in _consumers:
                if c["id"] == consumer_id:
                    c["active"] = True
                    c["exclusive"] = exclusive
                    print(f"🎤 Shared Mic: Activated '{c['name']}' (exclusive={exclusive})")
                    return
    
    @staticmethod
    def deactivate_consumer(consumer_id: str):
        """Deactivate a consumer."""
        with _lock:
            for c in _consumers:
                if c["id"] == consumer_id:
                    c["active"] = False
                    c["exclusive"] = False
                    print(f"🎤 Shared Mic: Deactivated '{c['name']}'")
                    return
    
    @staticmethod
    def deactivate_all_except(consumer_id: str):
        """Deactivate all consumers except one (for exclusive mode)."""
        with _lock:
            for c in _consumers:
                if c["id"] != consumer_id:
                    c["active"] = False
                    c["exclusive"] = False
    
    @staticmethod
    def is_running() -> bool:
        """Check if mic stream is running."""
        return _running
    
    @staticmethod
    def get_sample_rate() -> int:
        """Get the shared mic sample rate."""
        return SAMPLE_RATE


# Convenience functions
def start_shared_mic():
    """Start the shared microphone stream."""
    return MicStreamManager.start()

def stop_shared_mic():
    """Stop the shared microphone stream."""
    MicStreamManager.stop()

def register_mic_consumer(name: str, callback: Callable, priority: int = 0) -> str:
    """Register a microphone frame consumer."""
    return MicStreamManager.register_consumer(name, callback, priority)

def activate_mic_consumer(consumer_id: str, exclusive: bool = False):
    """Activate a mic consumer."""
    MicStreamManager.activate_consumer(consumer_id, exclusive)

def deactivate_mic_consumer(consumer_id: str):
    """Deactivate a mic consumer."""
    MicStreamManager.deactivate_consumer(consumer_id)
