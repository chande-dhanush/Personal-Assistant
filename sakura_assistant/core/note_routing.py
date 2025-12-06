import re
from typing import Optional, Dict, Any
from ..utils.note_tools import get_daily_note_title

def route_note_intent(user_input: str) -> Optional[Dict[str, Any]]:
    """
    Fast-path intent detection for note taking.
    Returns a tool call dict compatible with ActionRouter.
    """
    text = user_input.strip()
    
    # Regex patterns for capture
    # Group 1: Trigger, Group 2: Content (optional)
    # We use non-capturing groups (?:...) for the triggers
    patterns = [
        r"(?i)^(?:write this down|take a note|note that|add to notes|log this)(?:[:\s]+(?:that\s+)?)(.*)",
        r"(?i)^(?:remind me to|create a task to)(?:\s+)(.*)" # Task intent masquerading as note
    ]
    
    content = None
    
    # 1. Check specific capture patterns
    for p in patterns:
        match = re.match(p, text)
        if match:
            content = match.group(1).strip()
            break
            
    # 2. Check broad keywords if no specific match
    if not content:
        lower_text = text.lower()
        triggers = ["write this down", "take a note", "journal entry", "daily log"]
        if any(t in lower_text for t in triggers):
            # Use whole text if trigger is embedded or unclear
            content = text

    if not content:
        return None

    # 3. Determine Folder/Title
    folder = "topics"
    title = None
    action = "note_append"
    
    lower_content = content.lower()
    
    # Daily Note Logic
    if any(k in lower_content for k in ["today", "daily", "journal", "log"]):
        folder = "daily"
        title = get_daily_note_title()
    else:
        # Default to Daily for "quick notes" to avoid cluttering topics
        folder = "daily" 
        title = get_daily_note_title()

    return {
        "tool": action,
        "args": {
            "title": title,
            "content": content,
            "folder": folder
        }
    }
