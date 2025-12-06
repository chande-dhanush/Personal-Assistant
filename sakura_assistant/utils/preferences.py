import json
from pathlib import Path
from typing import Dict, List, Any, Optional
from ..memory.faiss_store.store import write_memory_atomic, DATA_DIR

PREFERENCES_FILE = DATA_DIR / "user_preferences.json"

class PreferenceStore:
    """
    Dedicated store for user preferences and profile data.
    Separates 'facts about user' from 'conversation history'.
    """
    def __init__(self):
        self.preferences = {
            "name": "User",
            "likes": [],
            "dislikes": [],
            "facts": {},
            "system_settings": {}
        }
        self._load()

    def _load(self):
        if PREFERENCES_FILE.exists():
            try:
                with open(PREFERENCES_FILE, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self.preferences.update(data)
            except Exception as e:
                print(f"⚠️ Error loading preferences: {e}")

    def save(self):
        write_memory_atomic(PREFERENCES_FILE, self.preferences)

    def set_preference(self, category: str, key: str, value: Any):
        """Set a specific preference (e.g. facts.age = 25)"""
        if category not in self.preferences:
            self.preferences[category] = {}
        
        if isinstance(self.preferences[category], list):
            if value not in self.preferences[category]:
                self.preferences[category].append(value)
        elif isinstance(self.preferences[category], dict):
            self.preferences[category][key] = value
            
        self.save()

    def get_profile_string(self) -> str:
        """Returns a formatted string of user preferences for the LLM system prompt."""
        lines = [f"User Name: {self.preferences.get('name', 'User')}"]
        
        if self.preferences.get('facts'):
            lines.append("Facts:")
            for k, v in self.preferences['facts'].items():
                lines.append(f"- {k}: {v}")
                
        if self.preferences.get('likes'):
            lines.append(f"Likes: {', '.join(self.preferences['likes'])}")
            
        if self.preferences.get('dislikes'):
            lines.append(f"Dislikes: {', '.join(self.preferences['dislikes'])}")
            
        return "\n".join(lines)

# Global Instance
user_preferences = PreferenceStore()

def get_user_profile() -> str:
    return user_preferences.get_profile_string()

def update_preference(category: str, key: str, value: Any):
    user_preferences.set_preference(category, key, value)
