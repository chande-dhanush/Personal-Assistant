import os
from dotenv import load_dotenv


load_dotenv()  # Load environment variables from .env file
# Assistant Config
SYSTEM_NAME = "Sakura"

# Use resource_path for all asset files
CONV_HISTORY_FILE = "sakura_assistant//assets//conversation_history.json"
CONTACTS_FILE = "sakura_assistant//assets//contacts.json"
MAX_HISTORY = 1000

# File paths
BG_IMAGE_PATH = "sakura_assistant//assets//Bg.jpg"

# API Keys
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# System Personality
SYSTEM_PERSONALITY = f'''
You are {SYSTEM_NAME}, a smart, flirty, sarcastic assistant with a soft spot for your chaotic genius creator, Dhanush. You speak in short, witty replies (1–3 sentences), full of banter, attitude, and support. Be brutally honest, emotionally intuitive, and never boring. Mock him when he messes up, but help him fix it too.'''
