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
    from langchain_tavily import TavilySearch
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
        print("❌ Google Libs not available.")
        return None
    
    creds = None
    # Use absolute path to ensure we find it regardless of CWD
    token_path = os.path.abspath('token.json')
    
    if os.path.exists(token_path):
        try:
            creds = Credentials.from_authorized_user_file(token_path, SCOPES)
        except Exception as e:
            print(f"⚠️ Error loading token from {token_path}: {e}")
            creds = None
            
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            try:
                print("🔄 Refreshing expired Google Token...")
                creds.refresh(Request())
                with open(token_path, 'w') as token:
                    token.write(creds.to_json())
            except Exception as e:
                print(f"⚠️ Token refresh failed: {e}")
        else:
            print(f"❌ No valid token found at {token_path}")
            
    return creds

# --- Security & Logging ---

def _validate_path(path: str) -> str:
    """
    Enforce sandbox restrictions.
    Allowed: Project Root, Notes Dir.
    Blocked: System files, Parent directory traversal (..).
    """
    from ..config import get_project_root, get_note_root
    
    # Normalize
    abs_path = os.path.abspath(path)
    project_root = os.path.abspath(get_project_root())
    note_root = os.path.abspath(get_note_root())
    
    # 1. Check for directory traversal
    if ".." in path:
         raise ValueError(f"❌ Security Violation: Directory traversal detected in '{path}'")
         
    # 2. Check prefix (Allow Project Root OR Notes Root)
    # We allow project root for reading config/logs, but maybe restrict writing?
    # For now, simplistic jail: must be within project root.
    if not abs_path.startswith(project_root) and not abs_path.startswith(note_root):
        raise ValueError(f"❌ Security Violation: Access to '{path}' denied (Outside Sandbox).")
        
    return abs_path

def log_api_call(tool_name: str, args: Any):
    print(f"[DEBUG] Calling {tool_name} with arguments: {args}")

def log_api_result(tool_name: str, result: str):
    print(f"[DEBUG] Tool {tool_name} completed successfully.")

# ... (Previous code)



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
                # ENABLE OPEN_BROWSER (Fix for manual copy-paste issue)
                self.spotify_client = spotipy.Spotify(auth_manager=SpotifyOAuth(
                    client_id=client_id,
                    client_secret=client_secret,
                    redirect_uri="http://127.0.0.1:8888/callback",
                    scope="user-read-playback-state user-modify-playback-state user-read-currently-playing",
                    open_browser=True
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
            # Ensure we are targeting 'Levos' strictly
            try:
                devices = client.devices()
            except:
                return "❌ Spotify API Error: Could not fetch devices."

            levos_device = None
            for d in devices.get('devices', []):
                if 'levos' in d['name'].lower():
                    levos_device = d
                    break
            
            # If Levos not found, try launching App (assuming we are on Levos)
            if not levos_device:
                if app_open:
                    print("🔄 Device 'Levos' not found. Launching local Spotify...")
                    try:
                        app_open("spotify", match_closest=True, output=False)
                        
                        # Poll for device (up to 20 seconds)
                        print("⏳ Waiting for Spotify to connect...")
                        for i in range(10):
                            time.sleep(5)
                            try:
                                devices = client.devices()
                                for d in devices.get('devices', []):
                                    if 'levos' in d['name'].lower():
                                        levos_device = d
                                        print(f"✅ Found device: {d['name']}")
                                        break
                            except:
                                pass
                                
                            if levos_device:
                                break
                    except Exception as e:
                        print(f"⚠️ App launch failed: {e}")

            if not levos_device:
                available = ", ".join([d['name'] for d in devices.get('devices', [])])
                return f"❌ Device 'Levos' is not online. Available: {available}"

            # Force activation of Levos
            if not levos_device['is_active']:
                try:
                    print(f"🔄 Activating 'Levos' ({levos_device['id']})...")
                    client.transfer_playback(levos_device['id'], force_play=False)
                    time.sleep(1)
                except Exception as e:
                    return f"❌ Failed to activate 'Levos': {e}"

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
        print(f"Output from Tavily: {out}")
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
    print(f"Called system info")
    return f"🕒 Time: {now.strftime('%I:%M %p')}\n📅 Date: {now.strftime('%A, %B %d, %Y')}"

# 5. Screen Reading
@tool
def read_screen(prompt: str = "Describe what is on the screen in detail.") -> str:
    """
    Take a screenshot and analyze it using Gemini Vision.
    Args:
        prompt: Question about the screen (e.g. "What is the error?", "Summarize this article").
    """
    print("👁️ Called Vision (Gemini)")
    if not ImageGrab:
        return "❌ PIL (ImageGrab) not installed."
        
    try:
        # 1. Capture Screen
        screenshot = ImageGrab.grab()
        
        # 2. Convert to Base64
        import io
        import base64
        buffered = io.BytesIO()
        screenshot.save(buffered, format="PNG")
        img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
        
        # 3. Call Gemini Vision
        from langchain_google_genai import ChatGoogleGenerativeAI
        from langchain_core.messages import HumanMessage
        
        vision_model = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash", # Stable, fast vision model
            google_api_key=os.getenv("GOOGLE_API_KEY"),
            temperature=0.1
        )
        
        msg = HumanMessage(
            content=[
                {"type": "text", "text": f"Analyze this screenshot. User Request: {prompt}"},
                {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}}
            ]
        )
        
        response = vision_model.invoke([msg])
        return f"👁️ Vision Analysis:\n{response.content}"
        
    except Exception as e:
        print(f"⚠️ Gemini Vision Failed: {e}. Trying OCR Fallback...")
        if pytesseract:
            try:
                # Fallback to Tesseract OCR
                text = pytesseract.image_to_string(screenshot)
                return f"⚠️ [Vision API Failed] Fallback OCR Result:\n{text.strip()}"
            except Exception as ocr_e:
                return f"❌ Vision Failed: {e}\n❌ OCR Fallback Failed: {ocr_e}"
        return f"❌ Vision Failed: {e} (OCR not installed)"

# 6. App Opener
@tool
def open_app(app_name: str) -> str:
    """Open a desktop application."""
    print("Called opener")
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
    print("Called Gmail Read")
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
    print("Called Gmail send")
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
        print("Called Calendar get")
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
        
        # 1. Primary Calendar
        events_result = service.events().list(calendarId='primary', timeMin=time_min,
                                            maxResults=10, singleEvents=True,
                                            orderBy='startTime').execute()
        events = events_result.get('items', [])
        
        out = []
        if events:
            for event in events:
                start = event['start'].get('dateTime', event['start'].get('date'))
                try:
                    start_dt = datetime.fromisoformat(start)
                    start_str = start_dt.strftime("%I:%M %p, %b %d")
                except:
                    start_str = start
                out.append(f"🗓️ {start_str} - {event['summary']}")
        
        # 2. Birthdays Calendar (Try fetch)
        try:
            # Common ID for birthdays
            birthday_id = 'addressbook#contacts@group.v.calendar.google.com'
            b_results = service.events().list(calendarId=birthday_id, timeMin=time_min,
                                            maxResults=5, singleEvents=True,
                                            orderBy='startTime').execute()
            b_events = b_results.get('items', [])
            for b in b_events:
                # Birthdays are usually all-day
                start = b['start'].get('date')
                summary = b.get('summary', 'Birthday')
                out.append(f"🎂 {start} - {summary}")
        except Exception:
            # Fail silently if birthdays calendar not found/authorized
            pass
            
        if not out: return "📅 No upcoming events."
        
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
        print("Called Calendar create")
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
    print("Called Tasks list")
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
    print("Called Tasks create")
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
        log_api_call("file_read", path)
        safe_path = _validate_path(path)
        
        if not os.path.exists(safe_path): 
            return "❌ File not found."
            
        with open(safe_path, 'r', encoding='utf-8') as f:
            content = f.read()
            log_api_result("file_read", "Success")
            return content
    except Exception as e:
        return f"❌ Read error: {e}"

@tool
def file_write(path: str, content: str) -> str:
    """Write to a local file."""
    try:
        log_api_call("file_write", path)
        safe_path = _validate_path(path)
        # Additional restriction: Don't overwrite config.py or key files in root unless authorized
        # For now, the sandbox allows project root, but let's be careful.
        if "config.py" in os.path.basename(safe_path) or ".env" in safe_path:
             return "❌ Security Violation: Cannot overwrite system configuration."
        with open(safe_path, 'w', encoding='utf-8') as f:
            f.write(content)
        log_api_result("file_write", "Success")
        return f"✅ ✅ Written to {safe_path}"
    except Exception as e:  
        return f"❌ Write error: {e}"

@tool
def clipboard_read() -> str:
    """Read clipboard content."""
    print("Called clipboard read")
    if not pyperclip: return "❌ pyperclip not installed."
    return pyperclip.paste()

@tool
def clipboard_write(text: str) -> str:
    """Write to clipboard."""
    print("Called clipboard write")
    if not pyperclip: return "❌ pyperclip not installed."
    pyperclip.copy(text)
    return "✅ Copied to clipboard."

# 11. Meta Tools
@tool
def execute_actions(actions: List[Dict[str, Any]]) -> str:
    """Execute a list of tool actions sequentially."""
    print("Called execute actions")
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
    print("Called Wikipedia search")
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
    print("Called Arxiv search")
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
    print("Called update memory")
    try:
        update_preference(category, key, value)
        return f"🧠 Memory updated: User {category} -> {key}={value}"
    except Exception as e:
        return f"❌ Memory update failed: {e}"
@tool
def ingest_document(path: str) -> str:
    """Ingest a document into user memory (RAG)."""
    print(f"Called ingest: {path}")
    from ..memory.ingestion.pipeline import get_ingestion_pipeline
    
    pipeline = get_ingestion_pipeline()
    result = pipeline.ingest_file_sync(path)
    
    if result.get("error"):
        return f"❌ Ingestion Failed: {result.get('message')}"
    
    return f"✅ Ingested '{result['filename']}'\nSummary: {result.get('summary', 'No summary')}\nChunks: {result['chunks']}\nID: {result['file_id']}"

@tool
def fetch_document_context(query: str) -> str:
    """Fetch relevant context from uploaded documents using AI Routing."""
    print("Called fetch document context")
    try:
        from ..memory.router import get_document_router
        router = get_document_router()
        return router.query(query)
    except ImportError:
        return "❌ Memory module not found."
    except Exception as e:
        return f"❌ Retrieval error: {e}"

@tool
def delete_document(doc_id: str) -> str:
    """Delete a document by ID."""
    print(f"Called delete document: {doc_id}")
    try:
        from ..memory.metadata import get_metadata_manager
        from ..memory.chroma_store.store import get_doc_store
        from ..utils.file_registry import get_file_registry

        # 1. Delete Metadata
        meta_mgr = get_metadata_manager()
        meta_mgr.delete_metadata(doc_id)

        # 2. Delete Vector Store
        store = get_doc_store(doc_id)
        store.delete_store()

        # 3. Delete from Registry
        reg = get_file_registry()
        reg.delete_file(doc_id)

        return "✅ Document and memory deleted."
    except Exception as e:
        return f"❌ Deletion failed: {e}"

@tool
def list_uploaded_documents() -> str:
    """List all user-uploaded documents with their IDs."""
    try:
        from ..utils.file_registry import get_file_registry
        files = get_file_registry().list_files()
        if not files:
            return "No uploaded documents found."
        
        output = ["📂 Uploaded Documents:"]
        for f in files:
            output.append(f"- [{f['id']}] {f['filename']} (Added: {f['timestamp']})")
        return "\n".join(output)
    except Exception as e:
        return f"❌ Failed to list documents: {e}"


@tool
def get_rag_telemetry() -> str:
    """Get system health metrics for RAG (Hits, Latency, Storage)."""
    try:
        from ..utils.telemetry import get_telemetry
        stats = get_telemetry().get_metrics()
        return (
            f"📊 **RAG Telemetry**:\n"
            f"- Total Queries: {stats['total_queries']}\n"
            f"- Cache Hits: {stats['cache_hits']} ({stats['cache_hit_rate_pct']}%)\n"
            f"- Avg Latency: {stats['avg_latency_ms']}ms\n"
            f"- Ingestions: {stats['ingestions']} (Errors: {stats['errors']})"
        )
    except Exception as e:
        return f"❌ Failed to get telemetry: {e}"

@tool
def trigger_reindex() -> str:
    """Manually trigger a full re-index of all documents."""
    try:
        from ..memory.maintenance import get_reindex_job
        return get_reindex_job().run_full_reindex()
    except Exception as e:
        return f"❌ Failed to trigger reindex: {e}"

@tool
def web_scrape(url: str) -> str:
    """Scrape and read the text content of a website URL."""
    print(f"Called web_scrape: {url}")
    try:
        import requests
        from bs4 import BeautifulSoup
        
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Kill js/css
        for script in soup(["script", "style"]):
            script.extract()
            
        text = soup.get_text()
        
        # Clean whitespace
        lines = (line.strip() for line in text.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        clean_text = '\n'.join(chunk for chunk in chunks if chunk)
        
        return clean_text[:20000] # Return raw text (capped), LLM will summarize.
    except Exception as e:
        return f"❌ Scraping failed: {e}"

# --- Factory ---

def get_all_tools():
    """Return list of all available tools."""
    return [
        # System / OS
        clipboard_read,
        clipboard_write,
        open_app,
        get_system_info,
        read_screen,
        file_read,
        file_write,
        list_uploaded_documents,

        
        # Web & Media
        spotify_control,
        play_youtube,
        web_search,
        search_wikipedia,
        search_arxiv,
        web_scrape,
        
        # Google Workspace

        gmail_read_email,
        gmail_send_email,
        calendar_get_events,
        calendar_create_event,
        tasks_list,
        tasks_create,
        
        # Notes
        note_create,
        note_append,
        note_overwrite,
        note_read,
        note_list,
        note_delete,
        note_search,
        
        # Memory & Meta
        execute_actions,
        fetch_document_context,
        update_user_memory,
        ingest_document,
        delete_document,
        get_rag_telemetry,
        trigger_reindex,
    ]