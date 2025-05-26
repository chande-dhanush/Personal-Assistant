import os
import asyncio
import pygame
import threading
from mutagen.mp3 import MP3
import edge_tts
from PyQt5 import QtCore

async def edge_tts_speak(text, voice="en-US-JennyNeural"):
    temp_file = "_sakura_tts.mp3"
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(temp_file)
        audio = MP3(temp_file)
        duration = int(audio.info.length * 1000)  # milliseconds
        
        pygame.mixer.init()
        pygame.mixer.music.load(temp_file)
        pygame.mixer.music.play()
        
        while pygame.mixer.music.get_busy():
            pygame.time.Clock().tick(10)
            
        pygame.mixer.music.unload()
        return duration
    finally:
        if os.path.exists(temp_file):
            os.remove(temp_file)

def text_to_speech(text, after_speech_callback=None):
    def run_tts():
        try:
            duration = asyncio.run(edge_tts_speak(text))
            if after_speech_callback:
                QtCore.QTimer.singleShot(duration, after_speech_callback)
        except Exception as e:
            print(f"TTS Error: {str(e)}")
    threading.Thread(target=run_tts, daemon=True).start() 