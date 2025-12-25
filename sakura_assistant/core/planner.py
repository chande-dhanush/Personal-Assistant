import json
from typing import Dict, Any
from langchain_core.messages import SystemMessage, HumanMessage
from ..config import GROQ_API_KEY

# Planner System Prompt
PLANNER_SYSTEM_PROMPT = """You are Sakura, the advanced planning engine. Your goal is to analyze the user's request and create a precise, step-by-step execution plan using the available tools.

AVAILABLE TOOLS:
1. spotify_control(action: str, song_name: str) - Play/Pause/Next/Previous music.
2. play_youtube(topic: str) - Play video/audio on YouTube.
3. web_search(query: str) - Search Google/Tavily for information.
4. read_screen(prompt: str) - Analyze the user's screen content.
5. gmail_read_email(query: str) - Read emails.
6. gmail_send_email(to: str, subject: str, body: str) - Send an email.
7. calendar_get_events(date: str) - Check calendar.
8. calendar_create_event(title: str, start_time: str, end_time: str) - Add to calendar.
9. tasks_list() - List Todo tasks.
10. tasks_create(title: str, notes: str) - Create a Todo task.
11. note_create(title: str, content: str, folder: str) - Create a note. Use folders: 'topics', 'daily', 'work', 'personal'.
12. note_append(title: str, content: str, folder: str) - Append to an existing note.
13. note_read(title: str, folder: str) - Read a note.
14. note_list(folder: str) - List notes in a folder.
15. file_read(path: str) - Read a local file (NOT for notes, use note_read).
16. file_write(path: str, content: str) - Write to a file (NOT for notes, use note_create).
17. fetch_document_context(query: str): Find information in uploaded documents (RAG).
18. list_uploaded_documents(): Get a list of all uploaded file names and IDs.
19. delete_document(doc_id: str): Remove an uploaded document from memory.
20. list_files(path: str) - List files in a directory.
21. web_scrape(url: str) - Scrape and read text from a website.
22. open_app(app_name: str) - Open any desktop application.


OUTPUT FORMAT:
You must output ONLY valid JSON. No markdown, no explanations.

Structure:
{
  "plan": [
    {
      "id": 1,
      "tool": "tool_name",
      "args": { "arg_name": "value" },
      "reason": "Short explanation of why this step is needed."
    }
  ]
}

RULES:
- If the request is simple chat (e.g., "Hi", "Who are you?", "Tell me a joke") and requires NO tools, return:
  { "plan": [] }
- You can create multiple steps (e.g., Search -> Write File).
- Arguments must be precise.
  - For Spotify: If user says "Play Mood", args: {"action": "play", "song_name": "Mood"}.
  - For YouTube: If user says "Play Mood on YouTube", args: {"topic": "Mood"}.
- NOTES: Only use note_create when user EXPLICITLY asks to "make a note", "save this", or "write down". Never create empty notes. The content arg must have actual text.
"""

# V4.2: Planner cache for idempotent commands (saves API calls)
# ONLY cache commands that are: deterministic, no arguments, no time-sensitivity
_CACHEABLE_PATTERNS = {
    "play spotify": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "play"}}]},
    "pause spotify": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "pause"}}]},
    "pause music": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "pause"}}]},
    "stop music": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "pause"}}]},
    "next track": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "next"}}]},
    "next song": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "next"}}]},
    "previous track": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "previous"}}]},
    "previous song": {"plan": [{"id": 1, "tool": "spotify_control", "args": {"action": "previous"}}]},
    "show calendar": {"plan": [{"id": 1, "tool": "calendar_get_events", "args": {}}]},
    "open calendar": {"plan": [{"id": 1, "tool": "calendar_get_events", "args": {}}]},
    "list tasks": {"plan": [{"id": 1, "tool": "tasks_list", "args": {}}]},
    "show tasks": {"plan": [{"id": 1, "tool": "tasks_list", "args": {}}]},
    "list notes": {"plan": [{"id": 1, "tool": "note_list", "args": {}}]},
    "show notes": {"plan": [{"id": 1, "tool": "note_list", "args": {}}]},
}


def _normalize_for_cache(text: str) -> str:
    """Normalize input for cache lookup."""
    return text.lower().strip()


class Planner:
    def __init__(self, llm):
        """
        Initialize Planner with a high-intelligence LLM (e.g., GPT-OSS-120b).
        """
        self.llm = llm

    def plan(self, user_input: str, context: str = "") -> Dict[str, Any]:
        """
        Generates a JSON execution plan.
        
        V4.2: Uses cache for idempotent commands to save API calls.
        """
        # V4.2: Check cache for idempotent commands
        from ..config import ENABLE_PLANNER_CACHE
        if ENABLE_PLANNER_CACHE:
            normalized = _normalize_for_cache(user_input)
            if normalized in _CACHEABLE_PATTERNS:
                print(f"⚡ Planner: Cache hit for '{normalized}'")
                return _CACHEABLE_PATTERNS[normalized]
        
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"User Request: {user_input}\nContext: {context}")
        ]

        try:
            print("🧠 Planner: Thinking...")
            response = self.llm.invoke(messages)
            content = response.content.strip()
            
            # Sanitization (Remove markdown if model hallucinates it)
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            plan_data = json.loads(content)
            
            # Validation
            if not isinstance(plan_data, dict) or "plan" not in plan_data:
                print(f"⚠️ Invalid Plan Format: {content}")
                return {"plan": []}
                
            print(f"📋 Planner Output: {len(plan_data['plan'])} steps.")
            return plan_data

        except json.JSONDecodeError:
            print(f"❌ Planner JSON Error. Raw: {content}")
            return {"plan": []}
        except Exception as e:
            print(f"❌ Planner Error: {e}")
            return {"plan": []}
