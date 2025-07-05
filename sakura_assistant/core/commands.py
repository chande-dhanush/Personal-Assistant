import re
import time
import os
import pywhatkit
import wikipedia
import pyjokes
import pyautogui
import spotipy
from spotipy.oauth2 import SpotifyOAuth
from ..utils.storage import load_contacts, add_contact
from ..utils.system import get_system_info, get_current_time, get_current_date
from ..config import SPOTIFY_CLIENT_ID, SPOTIFY_CLIENT_SECRET

# Initialize Spotify client
spotify_client = None
if SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET:
    try:
        print(f"Initializing Spotify client with Client ID: {SPOTIFY_CLIENT_ID[:5]}...")
        
        # Create cache directory if it doesn't exist
        cache_dir = os.path.join(os.path.dirname(__file__), '.spotify_cache')
        os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize Spotify client with OAuth
        spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
            client_id=SPOTIFY_CLIENT_ID,
            client_secret=SPOTIFY_CLIENT_SECRET,
            redirect_uri='http://127.0.0.1:8888/callback',
            scope='user-modify-playback-state user-read-playback-state',
            cache_path=os.path.join(cache_dir, '.spotify_token_cache'),
            open_browser=True
        ))
        
        # Test the connection
        try:
            devices = spotify_client.devices()
            if devices['devices']:
                print("Spotify client initialized successfully")
                print(f"Available devices: {[d['name'] for d in devices['devices']]}")
            else:
                print("No active Spotify devices found. Please open Spotify on your device.")
                spotify_client = None
        except Exception as e:
            print(f"Error testing Spotify connection: {str(e)}")
            spotify_client = None
            
    except Exception as e:
        print(f"Failed to initialize Spotify client: {str(e)}")
        spotify_client = None

def handle_spotify_play_command(user_input):
    song = user_input.replace('play the song', '').strip()
    
    if not spotify_client:
        return "Spotify integration is not configured. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables."
    
    try:
        # Search for the song
        results = spotify_client.search(song, limit=1, type='track')
        if not results['tracks']['items']:
            print(f"No results found for '{song}' on Spotify")
            return f"No results found for '{song}' on Spotify"
            
        track = results['tracks']['items'][0]
        print(f"Found track on Spotify: {track['name']} by {track['artists'][0]['name']}")
        
        # Get available devices
        devices = spotify_client.devices()
        if not devices['devices']:
            print("No Spotify devices found")
            return "No Spotify devices found. Please open Spotify on your device."
        
        # Try to find an active device
        active_device = None
        for device in devices['devices']:
            if device['is_active']:
                active_device = device
                break
        
        # If no active device, use the first available device
        if not active_device:
            active_device = devices['devices'][0]
            print(f"No active device found. Using device: {active_device['name']}")
            
            # Try to transfer playback to this device
            try:
                spotify_client.transfer_playback(device_id=active_device['id'], force_play=True)
                print(f"Transferred playback to {active_device['name']}")
            except Exception as e:
                print(f"Failed to transfer playback: {str(e)}")
                return f"Failed to activate Spotify device. Please make sure Spotify is open and playing."
        
        # Start playback on the selected device
        try:
            spotify_client.start_playback(
                device_id=active_device['id'],
                uris=[track['uri']]
            )
            return f"Playing {track['name']} by {track['artists'][0]['name']} on Spotify."
        except Exception as e:
            print(f"Failed to start playback: {str(e)}")
            return f"Failed to play song on Spotify. Please make sure Spotify is open and try again."
        
    except Exception as e:
        print(f"Spotify playback failed: {str(e)}")
        return f"Failed to play song on Spotify: {str(e)}"

def handle_youtube_play_command(user_input):
    video = user_input.replace('play the video', '').strip()
    try:
        pywhatkit.playonyt(video)
        return f"Playing {video} on YouTube."
    except Exception as e:
        return f"Failed to play video: {str(e)}"

def handle_whois_command(user_input):
    person = user_input.replace('who is', '').strip()
    try:
        info = wikipedia.summary(person, 1)
        return info
    except:
        return f"Sorry, I couldn't find information about {person}."

def handle_open_command(user_input):
    website = user_input.replace('open', '').strip()
    return f"Opening {website}. [ACTION: open_website \"{website}\"]"

def handle_message_command(user_input, assistant_ref):
    parts = user_input.split('to', 1)
    if len(parts) != 2:
        return "Invalid message format. Use: send message to [name] saying [message]"
    
    contacts = {k.lower(): v for k, v in load_contacts().items()}
    contact_name = parts[1].split('saying', 1)[0].strip()
    message = parts[1].split('saying', 1)[1].strip() if 'saying' in parts[1] else ""
    print(contacts)
    if not message:
        return "Invalid message format. Use: send message to [name] saying [message]"
    
    if contact_name not in contacts:
        return f"Contact {contact_name} not found."
        
    try:
        pywhatkit.sendwhatmsg_instantly(contacts[contact_name], message, 10, True, 2)
        time.sleep(10)
        pyautogui.press('alt+tab')
        time.sleep(1)
        pyautogui.press('enter')
        return f"Message sent to {contact_name}"
    except Exception as e:
        return f"Failed to send message: {str(e)}"

def handle_add_contact_command(user_input):
    tokens = user_input.split()
    if len(tokens) < 4:
        return "Usage: add contact [name] [number]"
        
    name = tokens[2]
    number = tokens[3]
    if add_contact(name, number):
        return f"Added {name} to contacts."
    return "Failed to add contact."

def handle_spotify_command(user_input):
    
    if not spotify_client:
        return "Spotify integration is not configured. Please set SPOTIFY_CLIENT_ID and SPOTIFY_CLIENT_SECRET environment variables."
    
    command = user_input.lower()
    try:
        # Check if there's an active device
        devices = spotify_client.devices()
        if not devices['devices']:
            return "No active Spotify devices found. Please open Spotify on your device."
            
        if 'pause' in command:
            spotify_client.pause_playback()
            return "Paused Spotify playback."
        elif 'resume' in command or 'play' in command:
            spotify_client.start_playback()
            return "Resumed Spotify playback."
        elif 'next' in command:
            spotify_client.next_track()
            return "Skipped to next track."
        elif 'previous' in command:
            spotify_client.previous_track()
            return "Playing previous track."
        elif 'volume' in command:
            # Extract volume level (0-100)
            try:
                volume = int(re.search(r'\d+', command).group())
                volume = max(0, min(100, volume))  # Clamp between 0-100
                spotify_client.volume(volume)
                return f"Set volume to {volume}%"
            except:
                return "Please specify a volume level between 0 and 100."
    except Exception as e:
        return f"Failed to control Spotify: {str(e)}"
    return None

import webbrowser

def watch_anime(user_input):
    user_input = user_input.lower()
    if 'i want to watch the anime' in user_input:
        user_input = user_input.replace('i want to watch the anime', '').strip()
    if 'open the anime' in user_input:
        user_input = user_input.replace('open the anime', '').strip()
    if 'i want to watch anime' in user_input:
        user_input = user_input.replace('i want to watch anime', '').strip()
    anime_name = user_input.strip()
    if anime_name:
        url = f"https://hianime.sx/search?keyword={anime_name}"
    else:
        url = "https://hianime.sx/home"
    
    try:
        # Open the URL in the default web browser
        webbrowser.open(url)
        if anime_name == "":
            return "Opening HiAnime homepage."
        return f"Searching for **{anime_name}**."
    except Exception as e:
        return f"An error occurred while trying to open the browser: {e}"

import requests

def handle_fun_apis(user_input):
    if 'anime quote' in user_input:
        try:
            res = requests.get('https://animechan.xyz/api/random')
            data = res.json()
            return f"“{data.get('quote')}” — {data.get('character')} ({data.get('anime')})"
        except:
            return "Failed to fetch anime quote."
    
    if 'give me advice' in user_input or 'some advice' in user_input:
        try:
            res = requests.get('https://api.adviceslip.com/advice')
            return res.json().get('slip', {}).get('advice', 'No advice found.')
        except:
            return "Failed to fetch advice."

    if 'bored' in user_input:
        try:
            res = requests.get('https://www.boredapi.com/api/activity')
            return res.json().get('activity', 'Try something new!')
        except:
            return "Failed to fetch activity."

    if 'search' in user_input:
        query = user_input.replace('search', '').strip().replace(' ', '+')
        try:
            res = requests.get(f'https://api.duckduckgo.com/?q={query}&format=json')
            abstract = res.json().get('Abstract')
            if abstract:
                return abstract
            else:
                return f"No quick result found, but you can search at: https://duckduckgo.com/?q={query}"
        except:
            return "Search failed."

    if 'weather' in user_input:
        try:
            # You can customize the location via lat/lon or use IP-based API instead
            res = requests.get('https://api.open-meteo.com/v1/forecast?latitude=12.97&longitude=77.59&current_weather=true')
            weather = res.json().get('current_weather', {})
            return f"The current temperature is {weather.get('temperature')}°C with wind speed {weather.get('windspeed')} km/h."
        except:
            return "Weather API failed."
    
    return None


def handle_command(user_input, chat_callback, assistant_ref=None):
    user_input_lower = user_input.lower()
    
    # Command mapping for cleaner code
    commands = {
        'play the song': lambda: handle_spotify_play_command(user_input_lower),
        'video': lambda: handle_youtube_play_command(user_input_lower),
        'who is': lambda: handle_whois_command(user_input_lower),
        'joke': lambda: pyjokes.get_joke(),
        'status': lambda: get_system_info(),
        'time': lambda: f"The current time is {get_current_time()}",
        'date': lambda: f"Today is {get_current_date()}",
        'open': lambda: handle_open_command(user_input_lower),
        'send a whatsapp message to': lambda: handle_message_command(user_input_lower, assistant_ref),
        'send a message to': lambda: handle_message_command(user_input_lower, assistant_ref),
        'message': lambda: handle_message_command(user_input_lower, assistant_ref),
        'add contact': lambda: handle_add_contact_command(user_input_lower),
        'spotify': lambda: handle_spotify_command(user_input_lower),
        'watch the anime': lambda: watch_anime(user_input_lower),
        'anime': lambda: watch_anime(user_input_lower),
        'anime quote': lambda: handle_fun_apis(user_input_lower),
        'give me advice': lambda: handle_fun_apis(user_input_lower),
        'bored': lambda: handle_fun_apis(user_input_lower),
        'search': lambda: handle_fun_apis(user_input_lower),
        'weather': lambda: handle_fun_apis(user_input_lower),
    }
    
    # Find matching command
    for cmd, handler in commands.items():
        if cmd in user_input_lower:
            return handler()
    return None 