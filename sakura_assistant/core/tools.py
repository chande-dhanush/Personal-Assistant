import os
import shutil
import time
import socket
from datetime import datetime, timedelta
import pytz
from typing import Optional, List, Dict, Any
import json
import functools

# Note Tools
from ..utils.note_tools import (
    note_create,
    note_append,
    note_overwrite,
    note_read,
    note_list,
    note_delete,
    note_search,
)

# LangChain helpers
from langchain_core.tools import tool
try:
    from langchain_tavily import TavilySearchResults
except ImportError:
    from langchain_community.tools.tavily_search import TavilySearchResults

# --- Third-party libs ---
try:
    import spotipy
    from spotipy.oauth2 import SpotifyOAuth
except ImportError:
    spotipy = None

try:
    from AppOpener import open as app_open
except ImportError:
    app_open = None

try:
    import pytesseract
    from PIL import ImageGrab
except ImportError:
    pytesseract = None
    ImageGrab = None

try:
    import pywhatkit
except ImportError:
    pywhatkit = None

try:
    import pyperclip
except ImportError:
    pyperclip = None

# Google APIs
try:
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from google.auth.transport.requests import Request
    from googleapiclient.discovery import build
    GOOGLE_AVAILABLE = True
except ImportError:
    GOOGLE_AVAILABLE = False

# --- Shared helpers and state ---
SCOPES = [
    'https://www.googleapis.com/auth/gmail.readonly',
    'https://www.googleapis.com/auth/gmail.send',
    'https://www.googleapis.com/auth/gmail.modify',
    'https://www.googleapis.com/auth/calendar',
    'https://www.googleapis.com/auth/tasks'
]

# CONSTANTS
USER_TIMEZONE = 'Asia/Kolkata'
socket.setdefaulttimeout(15) # Global timeout for safety

def get_google_creds():
    """Get valid Google Credentials."""
    if not GOOGLE_AVAILABLE:
        return None
    
    creds = None
    token_path = 'token.json'
    
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception:
            creds = None
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                creds.refresh(Request())
                # Save the credentials for the next run
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"⚠️ Token refresh failed: {e}")
    return creds

def retry_with_auth(func):
    """Decorator to retry Google API calls with re-auth if needed."""
    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            if "invalid_grant" in str(e) or "Token has been expired" in str(e):
                print("🔄 Token expired. Please re-authenticate.")
                return "❌ Auth token expired. Please restart to re-login."
            return func(*args, **kwargs) # Retry once or fail
    return wrapper

class ToolStateManager:
    _instance = None
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(ToolStateManager, cls).__new__(cls)
            cls._instance.spotify_client = None
            cls._instance._initialized = False
        return cls._instance

    def get_spotify(self):
        if not self.spotify_client:
            self._init_spotify()
        return self.spotify_client

    def _init_spotify(self):
        if not spotipy: return
        try:
            client_id = os.getenv("SPOTIFY_CLIENT_ID")
            client_secret = os.getenv("SPOTIFY_CLIENT_SECRET")
            if client_id and client_secret:
                self.spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri="http://127.0.0.1:8888/callback",
                    scope="user-read-playback-state user-modify-playback-state user-read-currently-playing",
                    open_browser=False
                ))
                print("✅ Spotify client initialized (Lazy Load).")
        except Exception as e:
            print(f"❌ Spotify init failed: {e}")

state_manager = ToolStateManager()

# --- Tool Definitions ---

# 1. Spotify (Smart)
@tool
def spotify_control(action: str, song_name: Optional[str] = None) -> str:
    """Control Spotify playback. 
    
    Args:
        action: 'play', 'pause', 'next', 'previous', or 'status'
        song_name: Name of song (only for 'play')
    """
    client = state_manager.get_spotify()
    
    # Auto-launch logic (Initial Check)
    if not client:
        # Try to open app first
        if app_open:
            print("🔄 Launching Spotify (Client Init)...")
            try:
                app_open("spotify", match_closest=True, output=False)
                time.sleep(5) # Wait for app to start
                state_manager._init_spotify() # Retry init
                client = state_manager.get_spotify()
            except:
                pass
            
    if not client:
        return "❌ Spotify not configured or unreachable. Please use 'play_youtube' instead."
    
    try:
        action = action.lower()
        if action == "play":
            # Ensure active device
            try:
                devices = client.devices()
            except:
                return "❌ Spotify API Error: Could not fetch devices."

            active_device = None
            levos_device = None
            
            if devices and devices.get('devices'):
                for d in devices['devices']:
                    if d['is_active']:
                        active_device = d
                    if d['name'].lower() == "levos":
                        levos_device = d
            
            # If no active device, try to activate Levos or launch app
            if not active_device:
                if levos_device:
                    print(f"🔄 Activating Levos ({levos_device['id']})...")
                    try:
                        client.transfer_playback(levos_device['id'], force_play=False)
                        time.sleep(1) 
                    except Exception as e:
                        print(f"⚠️ Failed to activate Levos: {e}")
                else:
                    # No Levos, no active device -> Launch App
                    print("🔄 No active device found. Launching Spotify...")
                    if app_open:
                        try:
                            app_open("spotify", match_closest=True, output=False)
                            time.sleep(5) 
                            
                            # Retry finding device after launch
                            for _ in range(3): 
                                devices = client.devices()
                                if devices and devices.get('devices'):
                                    target = devices['devices'][0]
                                    for d in devices['devices']:
                                        if d['name'].lower() == "levos":
                                            target = d
                                            break
                                    
                                    print(f"✅ Found device: {target['name']}")
                                    try:
                                        client.transfer_playback(target['id'], force_play=False)
                                        time.sleep(1)
                                        break
                                    except:
                                        pass
                                time.sleep(2)
                        except:
                            return "❌ Failed to launch Spotify application."
                    else:
                        return "❌ Spotify is not open and AppOpener is missing."

            # Now proceed with Play
            if song_name:
                results = client.search(q=song_name, limit=1, type="track")
                tracks = results.get("tracks", {}).get("items", [])
                if tracks:
                    client.start_playback(uris=[tracks[0]["uri"]])
                    return f"🎵 Playing '{tracks[0]['name']}'."
                return f"❌ Song '{song_name}' not found."
            else:
                client.start_playback()
                return "▶️ Resumed playback."
        elif action == "pause":
            client.pause_playback()
            return "⏸️ Paused."
        elif action == "next":
            client.next_track()
            return "⏭️ Skipped."
        elif action == "previous":
            client.previous_track()
            return "⏮️ Previous track."
        elif action == "status":
            current = client.current_playback()
            if current and current.get("is_playing"):
                item = current.get("item", {})
                return f"🎵 Now Playing: {item.get('name')} by {', '.join(a['name'] for a in item.get('artists', []))}"
            return "⏸️ Nothing playing."
        return "❌ Unknown action."
    except Exception as e:
        return f"❌ Spotify error: {e}"

# 2. YouTube
@tool
def play_youtube(topic: str) -> str:
    """Play a video or song on YouTube."""
    if not pywhatkit:
        return "❌ YouTube playback not available."
    try:
        pywhatkit.playonyt(topic)
        return f"📺 Playing '{topic}' on YouTube."
    except Exception as e:
        return f"❌ YouTube error: {e}"

# 3. Web Search
@tool
def web_search(query: str) -> str:
    """Search the web for information."""
    api_key = os.getenv("TAVILY_API_KEY")
    if not api_key:
        return "❌ TAVILY_API_KEY missing."
    try:
        tool = TavilySearchResults(max_results=5)
        results = tool.invoke({"query": query})
        out = [f"Search results for '{query}':"]
        for r in results:
            out.append(f"- {r['content']} ({r['url']})")
        return "\n\n".join(out)
    except Exception as e:
        return f"❌ Search failed: {e}"

# 4. System Info
@tool
def get_system_info() -> str:
    """Get current time and date."""
    now = datetime.now()
    return f"🕒 Time: {now.strftime('%I:%M %p')}\n📅 Date: {now.strftime('%A, %B %d, %Y')}"

# 5. Screen Reading
@tool
def read_screen() -> str:
    """Read text visible on screen."""
    if not pytesseract or not ImageGrab:
        return "❌ OCR not installed."
    try:
        text = pytesseract.image_to_string(ImageGrab.grab())
        return f"📄 Screen Text:\n{text[:500]}..." if text.strip() else "❌ No text found."
    except Exception as e:
        return f"❌ OCR Error: {e}"

# 6. App Opener
@tool
def open_app(app_name: str) -> str:
    """Open a desktop application."""
    if not app_open:
        return "❌ AppOpener not installed."
    try:
        app_open(app_name, match_closest=True, output=False)
        return f"🚀 Opened '{app_name}'."
    except Exception as e:
        return f"❌ Failed to open '{app_name}': {e}"

# 7. Gmail Tools
@tool
@retry_with_auth
def gmail_read_email(query: Optional[str] = None) -> str:
    """Read recent emails. Query can be 'from:user@example.com' etc."""
    creds = get_google_creds()
    if not creds: return "❌ Google Auth failed. Check token.json."
    
    try:
        service = build('gmail', 'v1', credentials=creds)
        q = query if query else "label:INBOX"
        results = service.users().messages().list(userId='me', q=q, maxResults=5).execute()
        messages = results.get('messages', [])
        
        if not messages: return "📭 No emails found."
        
        out = []
        for msg in messages:
            m = service.users().messages().get(userId='me', id=msg['id']).execute()
            snippet = m.get('snippet', '')
            headers = m['payload']['headers']
            subject = next((h['value'] for h in headers if h['name'] == 'Subject'), '(No Subject)')
            sender = next((h['value'] for h in headers if h['name'] == 'From'), '(Unknown)')
            out.append(f"📧 FROM: {sender}\n   SUBJ: {subject}\n   BODY: {snippet}...")
            
        return "\n\n".join(out)
    except Exception as e:
        return f"❌ Gmail error: {e}"

@tool
@retry_with_auth
def gmail_send_email(to: str, subject: str, body: str) -> str:
    """Send an email."""
    creds = get_google_creds()
    if not creds: return "❌ Google Auth failed."
    
    try:
        from email.mime.text import MIMEText
        import base64
        
        service = build('gmail', 'v1', credentials=creds)
        message = MIMEText(body)
        message['to'] = to
        message['subject'] = subject
        raw = base64.urlsafe_b64encode(message.as_bytes()).decode()
        
        service.users().messages().send(userId='me', body={'raw': raw}).execute()
        return f"📨 Email sent to {to}."
    except Exception as e:
        return f"❌ Send failed: {e}"

# 8. Calendar Tools
@tool
@retry_with_auth
def calendar_get_events(date: Optional[str] = None) -> str:
    """Get calendar events. Date format: YYYY-MM-DD (defaults to today)."""
    creds = get_google_creds()
    if not creds: return "❌ Google Auth failed."
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        
        # Calculate timeMin (default to start of today in User Timezone)
        tz = pytz.timezone(USER_TIMEZONE)
        if date:
            try:
                dt = datetime.strptime(date, "%Y-%m-%d")
                dt = tz.localize(dt)
            except:
                dt = datetime.now(tz)
        else:
            dt = datetime.now(tz)
            
        time_min = dt.isoformat()
        
        events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                            maxResults=10, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        if not events: return "📅 No upcoming events."
        
        out = []
        for event in events:
            start = event['start'].get('dateTime', event['start'].get('date'))
            # Convert to readable format if possible
            try:
                start_dt = datetime.fromisoformat(start)
                start_str = start_dt.strftime("%I:%M %p, %b %d")
            except:
                start_str = start
            out.append(f"🗓️ {start_str} - {event['summary']}")
            
        return "\n".join(out)
    except Exception as e:
        return f"❌ Calendar error: {e}"

@tool
@retry_with_auth
def calendar_create_event(title: str, start_time: str, end_time: str) -> str:
    """Create a calendar event. Times must be ISO format (YYYY-MM-DDTHH:MM:SS)."""
    creds = get_google_creds()
    if not creds: return "❌ Google Auth failed."
    
    try:
        service = build('calendar', 'v3', credentials=creds)
        event = {
            'summary': title,
            'start': {'dateTime': start_time, 'timeZone': USER_TIMEZONE},
            'end': {'dateTime': end_time, 'timeZone': USER_TIMEZONE},
        }
        event = service.events().insert(calendarId='primary', body=event).execute()
        return f"✅ Event created: {event.get('htmlLink')}"
    except Exception as e:
        return f"❌ Create event failed: {e}"

# 9. Tasks Tools
@tool
@retry_with_auth
def tasks_list() -> str:
    """List Google Tasks."""
    creds = get_google_creds()
    if not creds: return "❌ Google Auth failed."
    
    try:
        service = build('tasks', 'v1', credentials=creds)
        # Get default list
        tasklists = service.tasklists().list().execute()
        if not tasklists.get('items'): return "❌ No task lists found."
        
        list_id = tasklists['items'][0]['id']
        tasks = service.tasks().list(tasklist=list_id).execute()
        
        items = tasks.get('items', [])
        if not items: return "✅ No pending tasks."
        
        out = []
        for t in items:
            out.append(f"☐ {t['title']}")
        return "\n".join(out)
    except Exception as e:
        return f"❌ Tasks error: {e}"

@tool
@retry_with_auth
def tasks_create(title: str, notes: Optional[str] = None) -> str:
    """Create a Google Task."""
    creds = get_google_creds()
    if not creds: return "❌ Google Auth failed."
    
    try:
        service = build('tasks', 'v1', credentials=creds)
        tasklists = service.tasklists().list().execute()
        list_id = tasklists['items'][0]['id']
        
        task = {'title': title, 'notes': notes}
        service.tasks().insert(tasklist=list_id, body=task).execute()
        return f"✅ Task added: {title}"
    except Exception as e:
        return f"❌ Create task failed: {e}"

# 10. System Tools
@tool
def file_read(path: str) -> str:
    """Read a local file."""
    try:
        if not os.path.exists(path): return "❌ File not found."
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"❌ Read error: {e}"

@tool
def file_write(path: str, content: str) -> str:
    """Write to a local file."""
    try:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        return f"✅ Written to {path}"
    except Exception as e:
        return f"❌ Write error: {e}"

@tool
def clipboard_read() -> str:
    """Read clipboard content."""
    if not pyperclip: return "❌ pyperclip not installed."
    return pyperclip.paste()

@tool
def clipboard_write(text: str) -> str:
    """Write to clipboard."""
    if not pyperclip: return "❌ pyperclip not installed."
    pyperclip.copy(text)
    return "✅ Copied to clipboard."

# 11. Meta Tools
@tool
def execute_actions(actions: List[Dict[str, Any]]) -> str:
    """Execute a list of tool actions sequentially."""
    results = []
    tool_map = {t.name: t for t in get_all_tools() if t.name != 'execute_actions'}
    
    for action in actions:
        tool_name = action.get('tool')
        args = action.get('args', {})
        
        if tool_name not in tool_map:
            results.append(f"❌ Tool '{tool_name}' not found.")
            continue
            
        try:
            # Invoke tool
            res = tool_map[tool_name].invoke(args)
            results.append(f"▶️ {tool_name}: {res}")
        except Exception as e:
            results.append(f"❌ {tool_name} failed: {e}")
            
    return "\n\n".join(results)

def load_mcp_tools(server_url: str):
    """Scaffolding for MCP tool loading."""
    # TODO: Implement MCP client connection
    return []

# 12. Research Tools
@tool
def search_wikipedia(query: str) -> str:
    """Search Wikipedia for a summary."""
    try:
        import wikipedia
        # Set language to English
        wikipedia.set_lang("en")
        # Search for pages
        search_results = wikipedia.search(query, results=1)
        if not search_results:
            return "❌ No Wikipedia page found."
        
        page_title = search_results[0]
        summary = wikipedia.summary(page_title, sentences=3)
        return f"📚 Wikipedia ({page_title}):\n{summary}\n(Source: {wikipedia.page(page_title).url})"
    except ImportError:
        return "❌ 'wikipedia' library not installed."
    except Exception as e:
        return f"❌ Wikipedia error: {e}"

@tool
def search_arxiv(query: str) -> str:
    """Search Arxiv for scientific papers."""
    try:
        import arxiv
        client = arxiv.Client()
        search = arxiv.Search(
            query=query,
            max_results=3,
            sort_by=arxiv.SortCriterion.Relevance
        )
        
        results = []
        for r in client.results(search):
            results.append(f"📄 {r.title}\n   - Authors: {', '.join(a.name for a in r.authors)}\n   - Summary: {r.summary[:200]}...\n   - PDF: {r.pdf_url}")
            
        if not results:
            return "❌ No papers found."
            
        return "\n\n".join(results)
    except ImportError:
        return "❌ 'arxiv' library not installed."
    except Exception as e:
        return f"❌ Arxiv error: {e}"

# --- Memory Tools ---
from ..utils.preferences import update_preference

@tool
def update_user_memory(category: str, key: str, value: str) -> str:
    """
    Save a fact about the user for long-term memory.
    Args:
        category: 'facts' (static info), 'likes', 'dislikes'
        key: The specific fact (e.g. 'favorite_food' or 'hobbies')
        value: The value (e.g. 'Pizza' or 'Reading')
    Example: update_user_memory('likes', 'music', 'Jazz')
    """
    try:
        update_preference(category, key, value)
        return f"🧠 Memory updated: User {category} -> {key}={value}"
    except Exception as e:
        return f"❌ Memory update failed: {e}"
@tool
def fetch_document_context(query: str) -> str:
    """Fetch relevant context from uploaded documents/PDFs."""
    try:
        from ..memory.router import get_document_retriever
        retriever = get_document_retriever()
        if not retriever:
            return "❌ Document retrieval is disabled or failed to initialize."
            
        results = retriever.query(query)
        if not results:
            return "📭 No relevant document context found."
            
        out = [f"📄 Document Context for '{query}':"]
        for r in results:
            # Handle rich object
            content = r.get('content', '')
            meta = r.get('metadata', {})
            score = r.get('score', 0.0)
            
            source = f"{meta.get('filename', 'Unknown')}"
            if meta.get('page_number'):
                source += f" (Page {meta['page_number']})"
            
            out.append(f"--- {source} (Score: {score:.2f}) ---\n{content}\n")
            
        return "\n".join(out)
    except ImportError:
        return "❌ Memory module not found."
    except Exception as e:
        return f"❌ Retrieval error: {e}"

# --- Factory ---
def get_all_tools():
    """Return list of all available tools."""
    return [
        spotify_control,
        play_youtube,
        web_search,
        get_system_info,
        read_screen,
        open_app,
        # Google
        gmail_read_email,
        gmail_send_email,
        calendar_get_events,
        calendar_create_event,
        tasks_list,
        tasks_create,
        # System
        file_read,
        file_write,
        clipboard_read,
        clipboard_write,
        # Meta
        execute_actions,
        # Notes
        note_create,
        note_append,
        note_overwrite,
        note_read,
        note_list,
        note_delete,
        note_search,
        # Research
        search_wikipedia,
        search_arxiv,
        # Memory
        fetch_document_context,
        update_user_memory,
    ]