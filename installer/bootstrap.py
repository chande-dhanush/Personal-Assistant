import os
import sys
import subprocess
import shutil
import json
import platform

def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')

def print_header():
    print("===========================================")
    print("🌸 Sakura Assistant - Portable Installer 🌸")
    print("===========================================")

def check_python_version():
    if sys.version_info < (3, 10):
        print("❌ Error: Python 3.10 or higher is required.")
        print(f"Current version: {sys.version}")
        sys.exit(1)
    print("✅ Python version check passed.")

def create_venv():
    venv_dir = "sakura_env"
    if os.path.exists(venv_dir):
        print(f"ℹ️  Virtual environment '{venv_dir}' already exists.")
        return

    print(f"🔨 Creating virtual environment in '{venv_dir}'...")
    try:
        subprocess.check_call([sys.executable, "-m", "venv", venv_dir])
        print("✅ Virtual environment created.")
    except subprocess.CalledProcessError:
        print("❌ Failed to create virtual environment.")
        sys.exit(1)

def install_requirements():
    print("📦 Installing dependencies (this may take a while)...")
    pip_exe = os.path.join("sakura_env", "Scripts", "pip") if os.name == 'nt' else os.path.join("sakura_env", "bin", "pip")
    
    if not os.path.exists("requirements.txt"):
        print("⚠️ requirements.txt not found. Skipping installation.")
        return

    try:
        subprocess.check_call([pip_exe, "install", "-r", "requirements.txt"])
        print("✅ Dependencies installed.")
    except subprocess.CalledProcessError:
        print("❌ Failed to install dependencies.")
        sys.exit(1)

def setup_config():
    print("\n⚙️  Configuration Setup")
    
    # Defaults
    default_notes = os.path.expanduser("~/Documents/SakuraNotes")
    
    # User Prompts
    notes_dir = input(f"Where should notes be stored? [{default_notes}]: ").strip() or default_notes
    
    enable_spotify = input("Enable Spotify integration? (y/n) [n]: ").lower() == 'y'
    enable_google = input("Enable Google Workspace (Calendar/Gmail)? (y/n) [n]: ").lower() == 'y'
    
    # API Keys
    groq_key = input("Enter Groq API Key (Leave empty to skip): ").strip()
    google_key = input("Enter Google Gemini API Key (Leave empty to skip): ").strip()
    
    tavily_key = ""
    if input("Enable Web Search (Tavily)? (y/n) [n]: ").lower() == 'y':
        tavily_key = input("Enter Tavily API Key: ").strip()

    spotify_id = ""
    spotify_secret = ""
    if enable_spotify:
        spotify_id = input("Enter Spotify Client ID: ").strip()
        spotify_secret = input("Enter Spotify Client Secret: ").strip()

    # Timezone
    try:
        import tzlocal
        timezone = tzlocal.get_localzone_name()
    except ImportError:
        timezone = "Asia/Kolkata" # Fallback
    
    print(f"🌍 Detected Timezone: {timezone}")

    # Generate config.json
    config_data = {
        "notes_dir": notes_dir,
        "features": {
            "spotify": enable_spotify,
            "google_workspace": enable_google,
            "web_search": bool(tavily_key)
        }
    }
    
    with open("config.json", "w") as f:
        json.dump(config_data, f, indent=4)
        
    # Generate .env
    env_content = f"""GROQ_API_KEY={groq_key}
GOOGLE_API_KEY={google_key}
GOOGLE_CALENDAR_ENABLED={str(enable_google).lower()}
GOOGLE_GMAIL_ENABLED={str(enable_google).lower()}
TAVILY_API_KEY={tavily_key}
SPOTIFY_CLIENT_ID={spotify_id}
SPOTIFY_CLIENT_SECRET={spotify_secret}
USER_TIMEZONE={timezone}
"""
    with open(".env", "w") as f:
        f.write(env_content)
        
    print("✅ Configuration saved.")
    
    # Create Directories
    os.makedirs("logs", exist_ok=True)
    os.makedirs("data", exist_ok=True)
    os.makedirs("backups", exist_ok=True)
    os.makedirs(notes_dir, exist_ok=True)

def main():
    clear_screen()
    print_header()
    
    if os.name != 'nt':
        print("⚠️  Warning: This installer is optimized for Windows.")
    
    check_python_version()
    create_venv()
    install_requirements()
    setup_config()
    
    print("\n🎉 Installation Complete!")
    print("Run 'launch_sakura.bat' to start the assistant.")

if __name__ == "__main__":
    main()
