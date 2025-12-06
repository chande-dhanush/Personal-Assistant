import os
import asyncio
import pygame
import threading
import uuid
from mutagen.mp3 import MP3
import edge_tts

# Try to import pyttsx3 for offline fallback
try:
    import pyttsx3
    OFFLINE_AVAILABLE = True
except ImportError:
    OFFLINE_AVAILABLE = False

async def edge_tts_speak(text, voice="en-US-JennyNeural"):
    # Use unique filename to prevent locking issues
    temp_file = f"_sakura_tts_{uuid.uuid4().hex}.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_file)
        
        # Get duration for potential sync (optional)
        audio = MP3(temp_file)
        duration = int(audio.info.length * 1000)
        
        pygame.mixer.init()
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.music.unload()
        return duration
    finally:
        # Clean up
        if os.path.exists(temp_file):
            try:
                os.remove(temp_file)
            except Exception as e:
                print(f"⚠️ Failed to delete temp TTS file: {e}")

def run_edge_tts_sync(text):
    """Wrapper to run async Edge TTS in a thread."""
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        loop.run_until_complete(edge_tts_speak(text))
        loop.close()
    except Exception as e:
        print(f"⚠️ Edge TTS failed: {e}")
        # Fallback to offline
        run_offline_tts(text)

def run_offline_tts(text):
    if not OFFLINE_AVAILABLE:
        print("❌ Offline TTS not available (pyttsx3 missing).")
        return
        
    try:
        engine = pyttsx3.init()
        engine.setProperty('rate', 170)
        engine.say(text)
        engine.runAndWait()
    except Exception as e:
        print(f"❌ Offline TTS error: {e}")

def text_to_speech(text, after_speech_callback=None):
    """
    Main entry point. Tries Edge TTS (Online) -> pyttsx3 (Offline).
    Runs in a separate thread to avoid blocking UI.
    """
    def _run():
        # Try Online First
        try:
            run_edge_tts_sync(text)
        except:
            run_offline_tts(text)
            
        if after_speech_callback:
            after_speech_callback()

    threading.Thread(target=_run, daemon=True).start()