import json
import time
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

DATA_DIR = Path(__file__).parent.parent.parent / "data"
EPISODES_FILE = DATA_DIR / "user_episodes.json"

class EpisodicMemoryStore:
    """
    Manages dynamic 'episodic' memories - significant events, life updates, 
    and things the user specifically asked to recall.
    """
    def __init__(self):
        self.episodes: List[Dict] = []
        self._load()

    def _load(self):
        if EPISODES_FILE.exists():
            try:
                with open(EPISODES_FILE, 'r', encoding='utf-8') as f:
                    self.episodes = json.load(f)
            except Exception as e:
                print(f"⚠️ Error loading episodes: {e}")
                self.episodes = []
        else:
            self.episodes = []

    def save(self):
        try:
            with open(EPISODES_FILE, 'w', encoding='utf-8') as f:
                json.dump(self.episodes, f, indent=2, ensure_ascii=False)
        except Exception as e:
            print(f"❌ Error saving episodes: {e}")

    def add_episode(self, summary: str, tags: List[str] = None):
        """Adds a new episodic memory."""
        episode = {
            "summary": summary,
            "tags": tags or [],
            "date": time.strftime("%Y-%m-%d"),
            "timestamp": time.time()
        }
        self.episodes.append(episode)
        self.save()
        print(f"🧠 Episode stored: '{summary[:30]}...'")

    def search_episodes(self, query: str, limit: int = 3) -> List[Dict]:
        """
        Simple keyword-based retrieval for episodes.
        Returns top `limit` relevant episodes.
        """
        query_lower = query.lower()
        query_words = set(re.findall(r'\w+', query_lower))
        
        scored_episodes = []
        
        for ep in self.episodes:
            score = 0
            
            # Check tags
            for tag in ep.get('tags', []):
                if tag.lower() in query_lower:
                    score += 3  # Higher weight for tag match
            
            # Check summary text
            summary_lower = ep['summary'].lower()
            if query_lower in summary_lower:
                score += 5 # Exact phrase match
                
            # Word overlap
            ep_words = set(re.findall(r'\w+', summary_lower))
            overlap = len(query_words.intersection(ep_words))
            score += overlap
            
            if score > 0:
                scored_episodes.append((score, ep))
        
        # Sort by score descending
        scored_episodes.sort(key=lambda x: x[0], reverse=True)
        
        return [ep for _, ep in scored_episodes[:limit]]

    def get_recent_episodes(self, limit: int = 3) -> List[Dict]:
        """Returns the most recent episodes."""
        return sorted(self.episodes, key=lambda x: x.get('timestamp', 0), reverse=True)[:limit]

# Global Instance
episodic_memory = EpisodicMemoryStore()
