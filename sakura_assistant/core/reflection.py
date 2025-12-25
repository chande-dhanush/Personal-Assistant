import threading
import json
import time
from typing import List, Dict, Any
from langchain_groq import ChatGroq
from langchain_core.messages import SystemMessage, HumanMessage
from ..config import GROQ_API_KEY
from ..utils.preferences import update_preference, user_preferences
from ..utils.episodic_memory import episodic_memory

class ReflectionEngine:
    """
    The 'Subconscious Mind'.
    Analyzes recent interactions to extract long-term memories without user prompting.
    """
    def __init__(self):
        self._llm = None
        self._setup_llm()
        
    def _setup_llm(self):
        if GROQ_API_KEY:
            try:
                # Use a smaller/faster model for reflection to save cost/time
                self._llm = ChatGroq(
                    model="llama-3.1-8b-instant",  # Fast model for background tasks
                    temperature=0.1,  # Low temp for factual extraction
                    groq_api_key=GROQ_API_KEY
                )
            except Exception as e:
                print(f"⚠️ Reflection Engine Init Failed: {e}")

    def reflect_async(self, user_input: str, ai_response: str):
        """Starts reflection in a background thread."""
        if not self._llm: return
        
        # Don't reflect on short/trivial messages
        if len(user_input) < 10: return

        threading.Thread(
            target=self._run_reflection,
            args=(user_input, ai_response),
            daemon=True
        ).start()

    def _run_reflection(self, user_input: str, ai_response: str):
        """
        The core analysis logic.
        """
        try:
            # print("🧠 Subconscious: Reflecting on interaction...")
            
            system_prompt = (
                "You are the subconscious memory manager for an AI assistant.\n"
                "Your goal is to extract **permanent** and **significant** information about the user.\n"
                "Return a valid JSON object ONLY. No markdown, no explanations.\n\n"
                "**STRICT EXCLUSIONS (Do NOT store these):**\n"
                "- System errors, debugging logs, or troubleshooting steps (e.g. 'auth failed', 'token invalid').\n"
                "- Transient states (e.g. 'user is currently fixing a bug').\n"
                "- Short-term tasks that will be irrelevant tomorrow.\n"
                "- Trivial chit-chat (e.g. user said 'ok').\n\n"
                "**INCLUSIONS (Do store these):**\n"
                "- **Facts**: Updates to static identity (Name, Age, Job, Location, deeply held beliefs).\n"
                "- **Likes/Dislikes**: Permanent preferences (Music taste, Hobbies, Workflow habits).\n"
                "- **Episodes**: ONLY significant life events or meaningful conversations (Conversations that reveal character).\n\n"
                "JSON Schema:\n"
                "{\n"
                "  \"facts\": {\"key\": \"value\"},\n"
                "  \"likes\": [\"item1\"],\n"
                "  \"dislikes\": [\"item1\"],\n"
                "  \"episode\": {\n"
                "    \"summary\": \"One sentence description of significant event\",\n"
                "    \"tags\": [\"tag1\"]\n"
                "  }\n"
                "}\n\n"
                "If nothing new/significant is learned, return empty lists/dicts.\n"
                "Current User Profile for context:\n"
                f"{user_preferences.get_profile_string(full=True)}"
            )

            user_msg = f"UserID: User\nUser Input: {user_input}\nContext/Response: {ai_response}"
            
            messages = [
                SystemMessage(content=system_prompt),
                HumanMessage(content=user_msg)
            ]
            
            response = self._llm.invoke(messages)
            content = response.content
            
            # Clean generic markdown if present
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0]
            elif "```" in content:
                content = content.split("```")[1].split("```")[0]
                
            data = json.loads(content.strip())
            
            self._apply_updates(data)
            
        except Exception as e:
            # silently fail or log debug, don't crash main app
            print(f"⚠️ Reflection Error: {e}")

    def _apply_updates(self, data: Dict[str, Any]):
        changes_detected = False
        
        # 1. Facts
        if data.get("facts"):
            for k, v in data["facts"].items():
                # valid check: ensure key isn't huge
                if len(str(k)) < 50 and len(str(v)) < 100:
                    update_preference("facts", k, v)
                    print(f"🧠 Learned Fact: {k} = {v}")
                    changes_detected = True

        # 2. Likes
        if data.get("likes"):
            current_likes = user_preferences.get_likes()
            for item in data["likes"]:
                if item not in current_likes:
                    update_preference("likes", "", item) # Key is ignored for list appends
                    print(f"🧠 Learned Like: {item}")
                    changes_detected = True

        # 3. Dislikes
        if data.get("dislikes"):
            current_dislikes = user_preferences.get_dislikes()
            for item in data["dislikes"]:
                if item not in current_dislikes:
                    update_preference("dislikes", "", item)
                    print(f"🧠 Learned Dislike: {item}")
                    changes_detected = True
                    
        # 4. Episodes
        episode = data.get("episode")
        if episode and episode.get("summary"):
            episodic_memory.add_episode(episode["summary"], episode.get("tags", []))
            changes_detected = True

# Global Instance
reflection_engine = ReflectionEngine()
