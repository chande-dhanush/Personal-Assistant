# core/tools.py

import os
import subprocess
import time
import threading
import re
import json
import pywhatkit
import requests
import webbrowser
import platform
from datetime import datetime, timedelta
from typing import Optional, Dict, List
import asyncio
import aiohttp

from langchain.tools import tool, StructuredTool
from PIL import ImageGrab
import pytesseract

# Core utilities
from ..utils.storage import load_contacts, add_contact
from ..utils.system import get_system_info, get_current_time, get_current_date
from ..config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

# Enhanced imports
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import wikipediaapi
from duckduckgo_search import DDGS

# === Enhanced Configuration ===
USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"

# === Spotify Enhanced Setup ===
spotify_client = None
_current_device_id = None

def initialize_spotify():
    """Enhanced Spotify initialization with better error handling"""
    global spotify_client
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("⚠️ Spotify credentials missing in config.")
        return

    try:
        print("🎵 Initializing Spotify client...")
        cache_dir = os.path.join(os.path.dirname(__file__), ".spotify_cache")
        os.makedirs(cache_dir, exist_ok=True)

        auth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="user-modify-playback-state user-read-playback-state user-read-currently-playing playlist-read-private",
            cache_path=os.path.join(cache_dir, ".spotify_token_cache"),
            open_browser=True,
        )

        spotify_client = spotipy.Spotify(auth_manager=auth)
        
        # Start device monitoring
        threading.Thread(target=_enhanced_device_poller, daemon=True).start()
        print("✅ Spotify initialized successfully")
        
    except Exception as e:
        print(f"❌ Spotify initialization failed: {e}")
        spotify_client = None

def _enhanced_device_poller():
    """Enhanced device polling with fallback handling"""
    global _current_device_id
    while True:
        try:
            if not spotify_client:
                time.sleep(10)
                continue
                
            devices = spotify_client.devices().get('devices', [])
            if devices:
                # Prefer active device, fallback to first available
                active_device = next((d for d in devices if d['is_active']), None)
                if active_device:
                    _current_device_id = active_device['id']
                elif devices:
                    _current_device_id = devices[0]['id']
                    
        except Exception as e:
            print(f"⚠️ Device polling error: {e}")
        time.sleep(15)

# === Enhanced API Clients ===
class WeatherAPI:
    @staticmethod
    def get_weather(city: str = "Bengaluru") -> Dict:
        """Enhanced weather with multiple fallbacks"""
        try:
            # Primary: OpenWeather-like free API
            if city.lower() in ["bengaluru", "bangalore"]:
                lat, lon = 12.97, 77.59
            else:
                # For other cities, use geocoding
                lat, lon = WeatherAPI._geocode_city(city)
            
            url = f"https://api.open-meteo.com/v1/forecast"
            params = {
                "latitude": lat,
                "longitude": lon,
                "current_weather": True,
                "hourly": "temperature_2m,precipitation,weather_code",
                "daily": "temperature_2m_max,temperature_2m_min,precipitation_sum",
                "timezone": "auto",
                "forecast_days": 3
            }
            
            response = requests.get(url, params=params, timeout=10)
            return response.json()
            
        except Exception as e:
            return {"error": str(e)}
    
    @staticmethod
    def _geocode_city(city: str) -> tuple:
        """Simple geocoding fallback"""
        # You could integrate with a geocoding API here
        # For now, return Bengaluru coordinates as fallback
        return 12.97, 77.59

# Enhanced Wikipedia API
wiki_api = wikipediaapi.Wikipedia(
    language='en',
    extract_format=wikipediaapi.ExtractFormat.WIKI,
    user_agent=USER_AGENT
)

# === Core System Tools ===

@tool
def get_system_status() -> str:
    """Enhanced system information with more details"""
    try:
        info = get_system_info()
        # Add network info
        try:
            import psutil
            network = psutil.net_io_counters()
            info += f"\n📶 Network: {network.bytes_sent//1024//1024}MB sent, {network.bytes_recv//1024//1024}MB received"
        except:
            pass
        return info
    except Exception as e:
        return f"System info error: {e}"

@tool
def get_time_now() -> str:
    """Returns current time with timezone"""
    try:
        now = datetime.now()
        return f"Current time: {now.strftime('%I:%M %p')} on {now.strftime('%A, %B %d, %Y')}"
    except Exception as e:
        return f"Time error: {e}"

@tool
def get_date_now() -> str:
    """Returns detailed date information"""
    try:
        now = datetime.now()
        day_of_year = now.timetuple().tm_yday
        return f"Today is {now.strftime('%A, %B %d, %Y')} (Day {day_of_year} of the year)"
    except Exception as e:
        return f"Date error: {e}"

# === Enhanced Web & Search Tools ===

@tool
def advanced_web_search(query: str, num_results: int = 5) -> str:
    """Enhanced web search using DuckDuckGo with better results"""
    try:
        with DDGS() as ddgs:
            results = list(ddgs.text(query, max_results=num_results))
        
        if not results:
            return f"No search results found for: {query}"
        
        formatted_results = f"🔍 Search results for '{query}':\n\n"
        for i, result in enumerate(results, 1):
            formatted_results += f"{i}. **{result['title']}**\n"
            formatted_results += f"   {result['body'][:150]}...\n"
            formatted_results += f"   🔗 {result['href']}\n\n"
        
        return formatted_results
        
    except Exception as e:
        return f"Search failed: {e}. Try: https://duckduckgo.com/?q={query.replace(' ', '+')}"

@tool
def get_news_headlines(topic: str = "technology") -> str:
    """Get latest news headlines on a specific topic"""
    try:
        with DDGS() as ddgs:
            news = list(ddgs.news(topic, max_results=5))
        
        if not news:
            return f"No news found for topic: {topic}"
        
        headlines = f"📰 Latest news on '{topic}':\n\n"
        for i, article in enumerate(news, 1):
            headlines += f"{i}. **{article['title']}**\n"
            headlines += f"   📅 {article['date']}\n"
            headlines += f"   🔗 {article['url']}\n\n"
        
        return headlines
        
    except Exception as e:
        return f"News fetch failed: {e}"

@tool
def enhanced_wikipedia_search(topic: str) -> str:
    """Enhanced Wikipedia search with better formatting and error handling"""
    try:
        page = wiki_api.page(topic)
        
        if not page.exists():
            # Try search suggestions
            search_results = wiki_api.opensearch(topic, results=3)
            if len(search_results) > 2 and search_results[2]:
                suggestions = ", ".join(search_results[1][:3])
                return f"❌ '{topic}' not found. Did you mean: {suggestions}?"
            return f"❌ No Wikipedia page found for '{topic}'"
        
        # Get summary (first 3 sentences)
        summary = page.summary.split('. ')[:3]
        summary_text = '. '.join(summary) + '.'
        
        result = f"📖 **{page.title}**\n\n{summary_text}\n\n🔗 {page.fullurl}"
        
        # Add categories if available
        if page.categories:
            cats = list(page.categories.keys())[:3]
            result += f"\n\n🏷️ Categories: {', '.join(cats)}"
        
        return result
        
    except Exception as e:
        return f"Wikipedia search failed: {e}"

# === Enhanced Weather & Location Tools ===

@tool
def get_detailed_weather(city: str = "Bengaluru") -> str:
    """Enhanced weather information with forecast"""
    try:
        data = WeatherAPI.get_weather(city)
        
        if "error" in data:
            return f"Weather error: {data['error']}"
        
        current = data.get("current_weather", {})
        daily = data.get("daily", {})
        
        result = f"🌤️ **Weather in {city.title()}**\n\n"
        result += f"**Current:** {current.get('temperature', 'N/A')}°C\n"
        result += f"**Wind:** {current.get('windspeed', 'N/A')} km/h\n"
        
        # Add forecast if available
        if daily and "temperature_2m_max" in daily:
            result += f"\n**📅 3-Day Forecast:**\n"
            for i in range(min(3, len(daily["temperature_2m_max"]))):
                max_temp = daily["temperature_2m_max"][i]
                min_temp = daily["temperature_2m_min"][i]
                date = (datetime.now() + timedelta(days=i)).strftime("%a %b %d")
                result += f"• {date}: {min_temp}°C - {max_temp}°C\n"
        
        return result
        
    except Exception as e:
        return f"Weather fetch failed: {e}"

# === Enhanced Media & Entertainment Tools ===

@tool
def play_song_on_spotify(song_name: str) -> str:
    """Enhanced Spotify song playback with search results"""
    if not spotify_client:
        return "❌ Spotify not initialized. Please check credentials."

    try:
        # Search for multiple results
        results = spotify_client.search(song_name, limit=5, type="track")
        tracks = results['tracks']['items']
        
        if not tracks:
            return f"❌ No songs found for '{song_name}'"
        
        # Play the first result
        track = tracks[0]
        spotify_client.start_playback(device_id=_current_device_id, uris=[track['uri']])
        
        result = f"🎵 **Playing:** {track['name']}\n"
        result += f"👤 **Artist:** {', '.join(a['name'] for a in track['artists'])}\n"
        result += f"💽 **Album:** {track['album']['name']}\n"
        
        # Show alternatives if multiple found
        if len(tracks) > 1:
            result += f"\n**Other options found:**\n"
            for i, t in enumerate(tracks[1:3], 2):
                result += f"{i}. {t['name']} - {t['artists'][0]['name']}\n"
        
        return result
        
    except Exception as e:
        return f"❌ Spotify playback failed: {e}"

@tool
def get_spotify_status() -> str:
    """Get current Spotify playback status"""
    if not spotify_client:
        return "❌ Spotify not available"
    
    try:
        current = spotify_client.current_playback()
        if not current or not current.get('is_playing'):
            return "⏸️ Nothing is currently playing on Spotify"
        
        track = current['item']
        progress = current['progress_ms'] // 1000
        duration = track['duration_ms'] // 1000
        
        result = f"🎵 **Now Playing:**\n"
        result += f"🎵 {track['name']}\n"
        result += f"👤 {', '.join(a['name'] for a in track['artists'])}\n"
        result += f"⏱️ {progress//60}:{progress%60:02d} / {duration//60}:{duration%60:02d}\n"
        result += f"🔊 Volume: {current.get('device', {}).get('volume_percent', 'Unknown')}%"
        
        return result
        
    except Exception as e:
        return f"❌ Status check failed: {e}"

@tool
def control_spotify_playback(action: str) -> str:
    """Enhanced Spotify control with better feedback"""
    if not spotify_client:
        return "❌ Spotify not available"
    
    try:
        action = action.lower().strip()
        
        if action in ['pause', 'stop']:
            spotify_client.pause_playback()
            return "⏸️ Playback paused"
        elif action in ['play', 'resume']:
            spotify_client.start_playback()
            return "▶️ Playback resumed"
        elif action in ['next', 'skip']:
            spotify_client.next_track()
            return "⏭️ Skipped to next track"
        elif action in ['previous', 'back']:
            spotify_client.previous_track()
            return "⏮️ Went to previous track"
        elif action in ['shuffle']:
            current = spotify_client.current_playback()
            new_state = not current.get('shuffle_state', False)
            spotify_client.shuffle(new_state)
            return f"🔀 Shuffle {'enabled' if new_state else 'disabled'}"
        else:
            return f"❌ Unknown action '{action}'. Use: pause, play, next, previous, shuffle"
            
    except Exception as e:
        return f"❌ Control failed: {e}"

# === Enhanced Utility Tools ===

@tool
def get_inspirational_content() -> str:
    """Get inspirational quote, advice, or activity suggestion"""
    try:
        # Combine multiple APIs for variety
        content_type = time.time() % 3
        
        if content_type < 1:  # Advice
            response = requests.get("https://api.adviceslip.com/advice", timeout=5)
            advice = response.json().get("slip", {}).get("advice")
            return f"💡 **Advice:** {advice}"
            
        elif content_type < 2:  # Activity
            response = requests.get("https://www.boredapi.com/api/activity", timeout=5)
            activity = response.json().get("activity")
            activity_type = response.json().get("type", "").title()
            return f"🎯 **Activity Suggestion ({activity_type}):** {activity}"
            
        else:  # Anime quote
            response = requests.get("https://animechan.xyz/api/random", timeout=5)
            quote_data = response.json()
            return f"✨ **Anime Quote:**\n\"{quote_data['quote']}\"\n— {quote_data['character']} ({quote_data['anime']})"
            
    except Exception as e:
        return f"❌ Failed to get inspirational content: {e}"

@tool
def get_random_joke() -> str:
    """Get a random joke with variety"""
    try:
        import pyjokes
        joke_types = ['neutral', 'chuck', 'all']
        languages = ['en']
        
        joke = pyjokes.get_joke(
            language=languages[0], 
            category=joke_types[int(time.time()) % len(joke_types)]
        )
        return f"😄 {joke}"
        
    except Exception as e:
        return "😅 Why don't scientists trust atoms? Because they make up everything!"

# === Enhanced System Control Tools ===

@tool
def read_screen_text() -> str:
    """Enhanced screen reading with better error handling"""
    try:
        print("📸 Capturing screen...")
        screenshot = ImageGrab.grab()
        
        # Save temp file for debugging if needed
        text = pytesseract.image_to_string(screenshot)
        
        if not text.strip():
            return "📱 Screen captured but no readable text found"
        
        # Clean up the text
        lines = [line.strip() for line in text.split('\n') if line.strip()]
        cleaned_text = '\n'.join(lines[:20])  # Limit to first 20 lines
        
        return f"📖 **Screen Text:**\n{cleaned_text}"
        
    except Exception as e:
        return f"❌ Screen reading failed: {e}"

@StructuredTool.from_function
def open_anime_website() -> str:
    """Opens a random anime website"""
    try:
        webbrowser.open_new_tab("https://hianime.sx/")
        return "🌐 Anime website opened in new browser tab"
    except Exception as e:
        return f"❌ Failed to open anime website: {e}"

@StructuredTool.from_function
def smart_open_application(app_name: str) -> str:
    """Enhanced application launcher with common app shortcuts"""
    try:
        # Common application mappings
        app_shortcuts = {
            'chrome': ['chrome', 'google-chrome', 'google chrome'],
            'firefox': ['firefox', 'mozilla firefox'],
            'edge': ['msedge', 'microsoft edge'],
            'notepad': ['notepad', 'notepad.exe'],
            'calculator': ['calc', 'calculator'],
            'paint': ['mspaint', 'paint'],
            'explorer': ['explorer', 'file explorer'],
            'cmd': ['cmd', 'command prompt'],
            'powershell': ['powershell'],
            'vscode': ['code', 'visual studio code'],
            'spotify': ['spotify'],
        }
        
        app_lower = app_name.lower()
        actual_command = app_name
        
        # Find matching shortcut
        for cmd, aliases in app_shortcuts.items():
            if app_lower in aliases or any(alias in app_lower for alias in aliases):
                actual_command = cmd
                break
        
        system = platform.system()
        if system == "Windows":
            subprocess.Popen(["start", "", actual_command], shell=True)
        elif system == "Darwin":
            subprocess.Popen(["open", "-a", actual_command])
        else:
            subprocess.Popen([actual_command])
        
        return f"🚀 Launching {app_name}..."
        
    except Exception as e:
        return f"❌ Failed to open '{app_name}': {e}"

@StructuredTool.from_function
def smart_open_folder(path: str) -> str:
    """Enhanced folder opener with common shortcuts"""
    try:
        # Common folder shortcuts
        folder_shortcuts = {
            'desktop': os.path.join(os.path.expanduser('~'), 'Desktop'),
            'downloads': os.path.join(os.path.expanduser('~'), 'Downloads'),
            'documents': os.path.join(os.path.expanduser('~'), 'Documents'),
            'pictures': os.path.join(os.path.expanduser('~'), 'Pictures'),
            'music': os.path.join(os.path.expanduser('~'), 'Music'),
            'videos': os.path.join(os.path.expanduser('~'), 'Videos'),
            'home': os.path.expanduser('~'),
        }
        
        # Check for shortcuts
        path_lower = path.lower()
        if path_lower in folder_shortcuts:
            path = folder_shortcuts[path_lower]
        
        # Verify path exists
        if not os.path.exists(path):
            return f"❌ Path does not exist: {path}"
        
        system = platform.system()
        if system == "Windows":
            os.startfile(path)
        elif system == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        
        return f"📁 Opened folder: {path}"
        
    except Exception as e:
        return f"❌ Failed to open folder '{path}': {e}"

# === Quick Access Tools ===

@tool
def open_gmail() -> str:
    """Opens Gmail with better feedback"""
    try:
        webbrowser.open_new_tab("https://mail.google.com")
        return "📧 Gmail opened in new browser tab"
    except Exception as e:
        return f"❌ Failed to open Gmail: {e}"

@tool
def open_youtube() -> str:
    """Opens YouTube homepage"""
    try:
        webbrowser.open_new_tab("https://youtube.com")
        return "📺 YouTube opened in new browser tab"
    except Exception as e:
        return f"❌ Failed to open YouTube: {e}"

@tool
def play_youtube_video(video_query: str) -> str:
    """Enhanced YouTube video search and play with fallback options"""
    print(f"[DEBUG] play_youtube_video called with query: {video_query}")
    try:
        # First try with pywhatkit's direct search
        try:
            import pywhatkit
            print("[DEBUG] Attempting pywhatkit.playonyt...")
            pywhatkit.playonyt(video_query)
            print("[DEBUG] pywhatkit.playonyt succeeded")
            return f"🎥 Playing YouTube video for: '{video_query}'"
        except Exception as pyw_error:
            print(f"[DEBUG] pywhatkit failed: {pyw_error}, falling back to direct URL")
            # Fallback to manual URL construction if pywhatkit fails
            search_query = video_query.replace(' ', '+')
            url = f"https://www.youtube.com/results?search_query={search_query}"
            print(f"[DEBUG] Opening URL: {url}")
            webbrowser.open_new_tab(url)
            return f"🎥 Opened YouTube search for: '{video_query}' (using fallback method)"
    except Exception as e:
        print(f"[DEBUG] Critical error in play_youtube_video: {e}")
        return f"❌ YouTube search failed: {e}"

# === Final Tool Collection ===

def get_all_tools():
    """Return all available tools"""
    return [
        # Core system
        get_system_status,
        get_time_now,
        get_date_now,
        
        # Enhanced search & info
        advanced_web_search,
        get_news_headlines,
        enhanced_wikipedia_search,
        
        # Weather & location
        get_detailed_weather,
        
        # Media & entertainment
        play_song_on_spotify,
        get_spotify_status,
        control_spotify_playback,
        play_youtube_video,
        
        # Utilities & inspiration
        get_inspirational_content,
        get_random_joke,
        
        # System control
        read_screen_text,
        smart_open_application,
        smart_open_folder,
        
        # Quick access
        open_gmail,
        open_youtube,
        open_anime_website #to open anything regarding anime or hianime website
    ]