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

    def get_profile_string(self, full: bool = False) -> str:
        """
        Returns a formatted string of user preferences.
        If full=False, truncates lists and facts to save tokens.
        """
        lines = [f"User Name: {self.preferences.get('name', 'User')}"]
        
        # Helper to summarize list
        def summarize_list(lst, max_items=5):
            if not lst: return ""
            if len(lst) <= max_items or full:
                return ", ".join(lst)
            return ", ".join(lst[-max_items:]) + f" (+{len(lst)-max_items} more)"

        # 1. Facts
        facts = self.preferences.get('facts', {})
        if facts:
            lines.append("Facts:")
            if full:
                for k, v in facts.items():
                    lines.append(f"- {k}: {v}")
            else:
                # Show only first 3 facts in optimized mode
                items = list(facts.items())
                for k, v in items[:3]:
                    lines.append(f"- {k}: {v}")
                if len(items) > 3:
                     lines.append(f"... (+{len(items)-3} more facts)")

        # 2. Likes
        likes = self.preferences.get('likes', [])
        if likes:
            summary = summarize_list(likes)
            lines.append(f"Likes: {summary}")
            
        # 3. Dislikes
        dislikes = self.preferences.get('dislikes', [])
        if dislikes:
            summary = summarize_list(dislikes)
            lines.append(f"Dislikes: {summary}")
            
        return "\n".join(lines)

    def get_likes(self) -> List[str]:
        return self.preferences.get('likes', [])

    def get_dislikes(self) -> List[str]:
        return self.preferences.get('dislikes', [])

    def get_facts(self) -> Dict[str, Any]:
        return self.preferences.get('facts', {})

    def get_minimal_persona(self) -> str:
        """Returns just the vital personality specs (name, key traits)."""
        name = self.preferences.get('name', 'User')
        # Could theoretically include very high-level traits here if stored
        return f"User Name: {name}"

# Global Instance
user_preferences = PreferenceStore()

def get_user_profile() -> str:
    return user_preferences.get_profile_string()

def update_preference(category: str, key: str, value: Any):
    user_preferences.set_preference(category, key, value)
