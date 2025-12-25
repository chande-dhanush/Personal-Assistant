from typing import List, Dict, Any
from ..utils.preferences import user_preferences
from ..utils.episodic_memory import episodic_memory

class ContextManager:
    """
    Intelligent Context Injection.
    Decides WHAT to look up based on user input, instead of dumping everything.
    """
    def __init__(self):
        self.keywords_map = {
            "likes": ["like", "love", "enjoy", "prefer", "favorite", "recommend", "suggest", "anime", "movie", "book"],
            "dislikes": ["hate", "dislike", "avoid", "bad", "worst"],
            "facts": ["who am i", "my name", "my age", "where do i", "what do i do", "job", "work"],
            "episodes": ["remember", "happened", "last time", "when i", "told you", "said before", "recall", "memory", "know about me"]
        }

    def _detect_intent(self, text: str) -> List[str]:
        text = text.lower()
        intents = []
        for category, keywords in self.keywords_map.items():
            if any(k in text for k in keywords):
                intents.append(category)
        return intents

    def get_dynamic_context(self, user_input: str) -> str:
        """
        Builds a context string containing ONLY relevant info.
        """
        context_parts = []
        
        # 1. Always include minimal persona
        context_parts.append(f"=== USER IDENTITY ===\n{user_preferences.get_minimal_persona()}")

        # 2. Detect what else is needed
        intents = self._detect_intent(user_input)
        
        # 3. Fetch specific data
        if "likes" in intents:
            likes = user_preferences.get_likes()
            if likes:
                context_parts.append(f"=== RELEVANT LIKES ===\n{', '.join(likes)}")
                
        if "dislikes" in intents:
            dislikes = user_preferences.get_dislikes()
            if dislikes:
                context_parts.append(f"=== RELEVANT DISLIKES ===\n{', '.join(dislikes)}")
        
        if "facts" in intents:
            facts = user_preferences.get_facts()
            if facts:
                # For facts, we might want to be selective, but for now dumping them is better than nothing if requested
                # Ideally we'd keyword match facts too, but dictionary structure makes it easy enough to just dump if small
                # If facts grow large, we'll need a better search here.
                fact_str = "\n".join([f"- {k}: {v}" for k, v in facts.items()])
                context_parts.append(f"=== RELEVANT FACTS ===\n{fact_str}")

        if "episodes" in intents:
            # Search episodic memory using the user input as query
            hits = episodic_memory.search_episodes(user_input)
            if hits:
                episode_strs = [f"- [{ep['date']}] {ep['summary']}" for ep in hits]
                context_parts.append(f"=== RELEVANT MEMORIES ===\n" + "\n".join(episode_strs))
            else:
                # If they asked "what do you remember", but search failed, maybe show recent?
                recent = episodic_memory.get_recent_episodes(2)
                if recent:
                     episode_strs = [f"- [{ep['date']}] {ep['summary']}" for ep in recent]
                     context_parts.append(f"=== RECENT MEMORIES ===\n" + "\n".join(episode_strs))

        return "\n\n".join(context_parts)

# Global Instance
context_manager = ContextManager()

def get_smart_context(user_input: str, history: List[Dict]) -> Dict[str, str]:
    """
    Returns a dictionary of context metadata for the LLM.
    Combines User Dynamic Context + System State.
    """
    # 1. User Context (Likes, Memories, etc.)
    user_ctx = context_manager.get_dynamic_context(user_input)

    # 2. System Metadata (Last Tool, Routines)
    import re
    last_tool = "None"
    for msg in reversed(history[-5:]): 
        content = msg.get('content', '')
        # Check for our strict debug pattern
        match = re.search(r"\[DEBUG\] Calling (\w+)", content)
        if match:
            last_tool = match.group(1)
            break
            
    return {
        "dynamic_user_context": user_ctx,
        "last_tool_used": last_tool,
        "active_routines": "Morning Briefing (8AM), Evening Summary (11PM), Meeting Nudge",
        "short_memory_summary": "Active" # Placeholder for future summary
    }
