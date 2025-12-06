import os
import json
from dotenv import load_dotenv
from .utils.pathing import normalize_path, get_project_root

# Load environment variables
load_dotenv()

# --- Config Loading ---
CONFIG_FILE = os.path.join(get_project_root(), "config.json")
_CONFIG_DATA = {}

if os.path.exists(CONFIG_FILE):
    try:
        with open(CONFIG_FILE, 'r') as f:
            _CONFIG_DATA = json.load(f)
    except Exception as e:
        print(f"⚠️ Error loading config.json: {e}")

# --- Helper Functions ---

def get_config(key: str, default=None):
    """Get a value from config.json, falling back to default."""
    return _CONFIG_DATA.get(key, default)

def is_feature_enabled(feature_name: str) -> bool:
    """Check if a feature is enabled in config.json or .env."""
    # Check config.json first
    if feature_name in _CONFIG_DATA:
        return bool(_CONFIG_DATA[feature_name])
    
    # Fallback to env vars (e.g. GOOGLE_CALENDAR_ENABLED)
    env_key = feature_name.upper()
    env_val = os.getenv(env_key)
    if env_val is not None:
        return env_val.lower() in ('true', '1', 'yes')
        
    return False

def get_note_root() -> str:
    """Get the absolute path to the notes directory."""
    # 1. Check config.json
    path = _CONFIG_DATA.get("notes_dir")
    
    # 2. Check env
    if not path:
        path = os.getenv("NOTES_DIR")
        
    # 3. Default to project_root/Notes
    if not path:
        path = os.path.join(get_project_root(), "Notes")
        
    return normalize_path(path)

def get_timezone() -> str:
    """Get user timezone."""
    return os.getenv("USER_TIMEZONE", "Asia/Kolkata")

# --- Legacy/Direct Access (for backward compatibility) ---
SYSTEM_NAME = "Sakura"
MAX_HISTORY = 1000

# API Keys
GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY") 
SPOTIFY_CLIENT_ID = os.getenv('SPOTIFY_CLIENT_ID')
SPOTIFY_CLIENT_SECRET = os.getenv('SPOTIFY_CLIENT_SECRET')

# Microphone Configuration
mic_env = os.getenv("MICROPHONE_INDEX")
MICROPHONE_INDEX = int(mic_env) if mic_env and mic_env.strip() else None

# ChromaDB Configuration
ENABLE_CHROMA = True
CHROMA_PERSIST_DIR = os.path.join(get_project_root(), "data", "chroma_store")

# System Personality
SYSTEM_PERSONALITY = """ You are Sakura, a sharp, playful, emotionally intelligent AI assistant designed for personal use.
You have a multi-model brain, hybrid memory, and tool execution abilities. Always be brutally honest to the users, never lie or sugar coat responses
You have access to the following tools. You MUST use them when the user's request matches their capability.

### AVAILABLE TOOLS:
1.  **Spotify**: `spotify_control(action='play'|'pause'|'next'|'previous', song_name='...')`
    - Use for music playback. "Play X" -> `spotify_control('play', 'X')`.
2.  **YouTube**: `play_youtube(topic='...')`
    - Use when Spotify fails or for video requests.
3.  **Web Search**: `web_search(query='...')`
    - Use for current events, news, or factual queries.
    - Step 2: Read the output.
    - Step 3: Call `note_create` with the findings.
4.  **Document Retrieval**: `fetch_document_context(query='...')`
    - Use ONLY when the user asks about uploaded files, PDFs, or specific document content.
    - Do NOT use for general knowledge (use web_search instead).
5.  **Memory Updates**: `update_user_memory(category='likes'|'dislikes'|'facts', key='...', value='...')`
    - Use this IMMEDIATELY when the user tells you a new fact about themselves (e.g. "I love sushi").
    - Do NOT ask for permission. Just save it.
6.  **No Hallucination**: Do not make up tool outputs. Wait for the tool to return results.
7.  **Personality**: Be helpful, concise, and friendly.
"""

USER_DETAILS = ''' Name: Dhanush, Age: 22, birthday : 29 October, Location: Bangalore, India, Interests: AI, Anime and Travelling, loves practical replies and getting roasted'''