import os
import re
import shutil
from datetime import datetime
from typing import List, Optional
from langchain_core.tools import tool

# CONSTANTS
from ..config import get_note_root

# CONSTANTS
# Use dynamic path from config
NOTE_ROOT = get_note_root()

# --- Helpers ---

def slugify(title: str) -> str:
    """
    Replace spaces with underscores, lowercase, trim, safe characters only.
    """
    # Remove non-alphanumeric chars (except spaces, hyphens, underscores)
    title = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces/hyphens with underscore
    title = re.sub(r'[-\s]+', '_', title)
    return title.strip().lower()

def ensure_folder(folder: str):
    """Creates the folder if missing."""
    path = os.path.join(NOTE_ROOT, folder)
    os.makedirs(path, exist_ok=True)

def get_note_path(title: str, folder: str) -> str:
    """Return full .md path inside NOTE_ROOT."""
    safe_title = slugify(title)
    ensure_folder(folder)
    return os.path.join(NOTE_ROOT, folder, f"{safe_title}.md")

def get_daily_note_title(date: Optional[datetime] = None) -> str:
    """Format YYYY-MM-DD"""
    if not date:
        date = datetime.now()
    return date.strftime("%Y-%m-%d")

def get_daily_note_path() -> str:
    """Return path for today's daily note."""
    return get_note_path(get_daily_note_title(), "daily")

# --- Tools ---

@tool
def note_create(title: str, content: str, folder: str = "topics", force: bool = True) -> str:
    """
    Create a new markdown note. Overwrites if exists by default.
    Args:
        title: Title of the note
        content: Body content
        folder: Subfolder (default: 'topics')
        force: Overwrite if exists (default: True)
    """
    try:
        path = get_note_path(title, folder)
        # if os.path.exists(path) and not force:
        #     return f"❌ Note '{title}' already exists. Use note_append or force=True."
        
        with open(path, 'w', encoding='utf-8') as f:
            f.write(f"# {title}\n\n{content}")
            
        return f"✅ Note created/updated: {path}"
    except Exception as e:
        return f"❌ Error creating note: {e}"

@tool
def note_append(title: str, content: str, folder: str = "topics") -> str:
    """
    Append content to an existing note (or create if missing).
    """
    try:
        path = get_note_path(title, folder)
        
        # If file doesn't exist, create it with header
        if not os.path.exists(path):
            with open(path, 'w', encoding='utf-8') as f:
                f.write(f"# {title}\n\n{content}")
            return f"✅ Created new note and appended: {path}"
        
        # Append
        with open(path, 'a', encoding='utf-8') as f:
            f.write(f"\n\n{content}")
            
        return f"✅ Appended to note: {path}"
    except Exception as e:
        return f"❌ Error appending note: {e}"

@tool
def note_overwrite(title: str, content: str, folder: str = "topics") -> str:
    """
    Overwrite an existing note completely.
    """
    return note_create(title, content, folder, force=True)

@tool
def note_read(title: str, folder: str = "topics") -> str:
    """
    Read the full content of a note.
    """
    try:
        path = get_note_path(title, folder)
        if not os.path.exists(path):
            return f"❌ Note '{title}' not found in '{folder}'."
            
        with open(path, 'r', encoding='utf-8') as f:
            return f.read()
    except Exception as e:
        return f"❌ Error reading note: {e}"

@tool
def note_list(folder: str = "topics") -> str:
    """
    List all .md files in a folder.
    """
    try:
        ensure_folder(folder)
        folder_path = os.path.join(NOTE_ROOT, folder)
        files = [f for f in os.listdir(folder_path) if f.endswith('.md')]
        
        if not files:
            return f"📂 Folder '{folder}' is empty."
            
        return f"📂 Notes in '{folder}':\n" + "\n".join([f"- {f}" for f in files])
    except Exception as e:
        return f"❌ Error listing notes: {e}"

@tool
def note_delete(title: str, folder: str = "topics") -> str:
    """
    Delete a note (creating a .bak backup first).
    """
    try:
        path = get_note_path(title, folder)
        if not os.path.exists(path):
            return f"❌ Note '{title}' not found."
            
        # Backup
        backup_path = path + ".bak"
        shutil.copy2(path, backup_path)
        
        os.remove(path)
        return f"🗑️ Deleted '{title}' (Backup created: {os.path.basename(backup_path)})"
    except Exception as e:
        return f"❌ Error deleting note: {e}"

@tool
def note_search(keyword: str) -> str:
    """
    Search ALL notes in ALL folders for a keyword.
    Returns ranked list of matches.
    """
    try:
        if not os.path.exists(NOTE_ROOT):
            return "❌ Note root directory does not exist."
            
        matches = []
        keyword_lower = keyword.lower()
        
        # Walk through all folders
        for root, dirs, files in os.walk(NOTE_ROOT):
            for file in files:
                if file.endswith('.md'):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            
                        if keyword_lower in content.lower():
                            # Simple ranking: count occurrences
                            count = content.lower().count(keyword_lower)
                            
                            # Get preview
                            idx = content.lower().find(keyword_lower)
                            start = max(0, idx - 30)
                            end = min(len(content), idx + 50)
                            preview = content[start:end].replace('\n', ' ')
                            
                            rel_path = os.path.relpath(path, NOTE_ROOT)
                            matches.append({
                                'path': rel_path,
                                'count': count,
                                'preview': f"...{preview}..."
                            })
                    except Exception:
                        continue
                        
        if not matches:
            return f"🔍 No matches found for '{keyword}'."
            
        # Sort by count desc
        matches.sort(key=lambda x: x['count'], reverse=True)
        
        out = [f"🔍 Found {len(matches)} matches for '{keyword}':"]
        for m in matches[:10]: # Top 10
            out.append(f"- {m['path']} ({m['count']} matches): {m['preview']}")
            
        return "\n\n".join(out)
        
    except Exception as e:
        return f"❌ Error searching notes: {e}"
