# core/tools.py

import os
import subprocess
import time
import threading
import re
import pywhatkit
import wikipedia
import pyjokes
import pyautogui
import webbrowser
import requests

from langchain.tools import tool, StructuredTool

from ..utils.storage import load_contacts, add_contact
from ..utils.system import (
    get_system_info,
    get_current_time,
    get_current_date
)
from ..config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET
from spotipy.oauth2 import SpotifyOAuth
import spotipy

# === Spotify Initialization ===

spotify_client = None
_current_device_id = None

def initialize_spotify():
    """Run once during app init"""
    global spotify_client
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        print("⚠️ Spotify credentials missing.")
        return

    try:
        print(f"🔑 Initializing Spotify client...")

        cache_dir = os.path.join(os.path.dirname(__file__), ".spotify_cache")
        os.makedirs(cache_dir, exist_ok=True)

        auth = SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri="http://127.0.0.1:8888/callback",
            scope="user-modify-playback-state user-read-playback-state user-read-currently-playing",
            cache_path=os.path.join(cache_dir, ".spotify_token_cache"),
            open_browser=True,
        )

        spotify_client = spotipy.Spotify(auth_manager=auth)
        threading.Thread(target=_device_poller, daemon=True).start()
    except Exception as e:
        print(f"Spotify init failed: {e}")
        spotify_client = None


def _device_poller():
    """Poll for active Spotify device every 15s"""
    global _current_device_id
    while True:
        try:
            if not spotify_client:
                time.sleep(5)
                continue
            devices = spotify_client.devices().get('devices', [])
            if devices:
                target = next((d for d in devices if d['is_active']), devices[0])
                _current_device_id = target['id']
        except Exception as e:
            print(f"⚠️ Spotify device poll failed: {e}")
        time.sleep(15)

# === Tools ===


@tool
def get_system_status() -> str:
    """Shows current system information like CPU and memory."""
    return get_system_info()


@tool
def get_time_now() -> str:
    """Returns the current time as string."""
    return f"The current time is {get_current_time()}"


@tool
def get_date_now() -> str:
    """Returns the current date."""
    return f"Today is {get_current_date()}"


@tool
def get_a_joke() -> str:
    """Tells a programming-related joke."""
    return pyjokes.get_joke()


@tool
def open_gmail() -> str:
    """Opens Gmail in a browser."""
    try:
        webbrowser.open_new("https://mail.google.com")
        return "Gmail opened in your browser."
    except Exception as e:
        return f"Failed to open Gmail: {e}"


@tool
def get_weather_bengaluru() -> str:
    """Returns current temperature in Bengaluru."""
    try:
        res = requests.get("https://api.open-meteo.com/v1/forecast?latitude=12.97&longitude=77.59&current_weather=true")
        weather = res.json().get("current_weather", {})
        temp = weather.get("temperature")
        wind = weather.get("windspeed")
        return f"Bengaluru: {temp}°C, Wind speed: {wind} km/h"
    except Exception as e:
        return f"Weather fetch failed: {str(e)}"


@tool
def open_hianime_homepage() -> str:
    """Opens HiAnime homepage for browsing anime."""
    try:
        webbrowser.open("https://hianime.sx/home")
        return "Opened HiAnime homepage."
    except Exception as e:
        return f"Could not open HiAnime: {e}"


@tool
def get_random_advice() -> str:
    """Fetches a random advice from AdviceSlip API."""
    try:
        res = requests.get("https://api.adviceslip.com/advice")
        return res.json().get("slip", {}).get("advice", "No advice found.")
    except:
        return "Failed to get advice."


@tool
def get_anime_quote() -> str:
    """Fetches a random anime quote from AnimeChan API."""
    try:
        res = requests.get("https://animechan.xyz/api/random")
        q = res.json()
        return f"“{q['quote']}” — {q['character']} ({q['anime']})"
    except:
        return "Failed to fetch anime quote."


@tool
def get_random_activity() -> str:
    """Fetches a random BoredAPI activity suggestion."""
    try:
        res = requests.get("https://www.boredapi.com/api/activity")
        return res.json().get("activity", "Try doing something creative!")
    except:
        return "Failed to get random activity."


@tool
def open_web_search(query: str) -> str:
    """Searches a query using DuckDuckGo & returns summary."""
    try:
        url = f"https://api.duckduckgo.com/?q={query}&format=json"
        res = requests.get(url).json()
        abstract = res.get('Abstract')
        if abstract:
            return abstract
        return f"No answer found. Try searching: https://duckduckgo.com/?q={query.replace(' ', '+')}"
    except:
        return "Search failed."


# === Structured Arguments Tools ===
from langchain.tools import StructuredTool

@tool
def play_song_on_spotify(song_name: str) -> str:
    """Play a specific song on Spotify."""
    return play_song(song_name)

@tool
def control_spotify_playback(action: str) -> str:
    """Control Spotify playback — use 'pause', 'play', 'next', or 'previous'."""
    return spotify_control(action)

@tool
def search_wikipedia(query: str) -> str:
    """Search and summarize a topic using Wikipedia."""
    return wikipedia.summary(query, sentences=2)


@tool
def play_video_on_youtube(video_title: str) -> str:
    """Play a video on YouTube by title."""
    try:
        pywhatkit.playonyt(video_title)
        return f"Playing '{video_title}' on YouTube."
    except Exception as e:
        return f"Failed to play YouTube video: {e}"

# === Internal Logic for Spotify Tools ===

def play_song(song_name: str) -> str:
    if not spotify_client:
        return "Spotify not initialized."

    try:
        results = spotify_client.search(song_name, limit=1, type="track")
        track = results['tracks']['items'][0]
        spotify_client.start_playback(device_id=_current_device_id, uris=[track['uri']])
        return f"Playing {track['name']} by {track['artists'][0]['name']}."
    except Exception as e:
        return f"Failed to play Spotify song: {e}"


def spotify_control(action: str) -> str:
    try:
        if not spotify_client:
            return "Spotify not available."
        if 'pause' in action:
            spotify_client.pause_playback()
        elif 'play' in action or 'resume' in action:
            spotify_client.start_playback()
        elif 'next' in action:
            spotify_client.next_track()
        elif 'previous' in action:
            spotify_client.previous_track()
        else:
            return "Invalid control action."
        return f"Executed playback action: {action}"
    except Exception as e:
        return f"Error controlling Spotify: {e}"
import platform
from PIL import ImageGrab  # For screenshot
import pytesseract


@tool
def read_screen_text() -> str:
    """
    Captures the current screen and returns any readable text.
    Triggered only when the user requests 'read screen' or 'what's on the screen'.
    """
    try:
        image = ImageGrab.grab()
        text = pytesseract.image_to_string(image)
        return text if text.strip() else "I couldn't read any text on the screen."
    except Exception as e:
        return f"Screen reading failed: {str(e)}"


@StructuredTool.from_function
def open_folder(path: str) -> str:
    """
    Opens a folder or path on your system using the file explorer.
    Provide full or relative folder path.
    """
    try:
        if platform.system() == "Windows":
            os.startfile(path)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", path])
        else:
            subprocess.Popen(["xdg-open", path])
        return f"Opened folder: {path}"
    except Exception as e:
        return f"Failed to open folder '{path}': {e}"


@StructuredTool.from_function
def open_application(app_name: str) -> str:
    """
    Opens an installed application by name. Ex: 'notepad', 'chrome', 'vlc'.
    Make sure the app is available in your system PATH or specify the full path.
    """
    try:
        if platform.system() == "Windows":
            subprocess.Popen(["start", "", app_name], shell=True)
        elif platform.system() == "Darwin":
            subprocess.Popen(["open", "-a", app_name])
        else:
            subprocess.Popen([app_name])
        return f"Launching application: {app_name}"
    except Exception as e:
        return f"Failed to open application '{app_name}': {e}"

# === Final Tool Export ===

def get_all_tools():
    return [
        get_system_status,
        get_time_now,
        get_date_now,
        get_a_joke,
        open_gmail,
        get_weather_bengaluru,
        open_hianime_homepage,
        get_random_advice,
        get_anime_quote,
        get_random_activity,
        open_web_search,
        search_wikipedia,
        play_video_on_youtube,
        play_song_on_spotify,
        control_spotify_playback,
        read_screen_text,
        open_folder,
        open_application,
    ]
