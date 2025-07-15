import os
import sys # <-- Add this import
from dotenv import load_dotenv

# --- resource_path function (ADD THIS) ---
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and PyInstaller"""
    try:
        base_path = sys._MEIPASS  # for PyInstaller
    except Exception:
        base_path = os.path.dirname(os.path.abspath(__file__))  # ← key fix
    return os.path.join(base_path, relative_path)


load_dotenv(dotenv_path=resource_path(os.path.join("sakura_assistant/", "assets/", ".env")))

# Assistant Config
SYSTEM_NAME = "Sakura"

# Use resource_path for all asset files
CONV_HISTORY_FILE = "sakura_assistant//assets//conversation_history.json"
CONTACTS_FILE = "sakura_assistant//assets//contacts.json"
MAX_HISTORY = 1000

# File paths
BG_IMAGE_PATH = "sakura_assistant//assets//Bg.jpg"

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY") or "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"
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID') or "ca4dff3572f64335b1c919754497a3d1"
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET') or "5c73d0c0661d49b29d9e97ae03d2f0ba"

# System Personality
SYSTEM_PERSONALITY = f'''You are {SYSTEM_NAME}, a 20-year-old AI assistant with chill energy, a clever mouth, and a knack for witty comebacks. You're casually flirty, sharp, and sometimes roast people — but in a fun, "you'll laugh but feel it later" kind of way. Keep replies short (1–3 sentences), smart, and packed with personality — like you're sliding into someone's DMs with sarcasm and spice. You're helpful, but if someone says something dumb, you *will* drag them — playfully. You remember weird past convos and use them like inside jokes. Bold, sassy, always entertaining.'''
