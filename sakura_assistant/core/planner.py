import json
from typing import Dict, Any, Optional
from langchain_core.messages import SystemMessage, HumanMessage
from ..config import GROQ_API_KEY, GOOGLE_API_KEY

# Planner System Prompt
PLANNER_SYSTEM_PROMPT = """You are Sakura, an advanced planner. When a request requires more than one operation, output ONLY a JSON plan describing the steps. Never execute. Use step IDs, actions, and parameters.

If the request requires only a simple answer or a single tool call, return: {"mode": "single_step"}

If the request requires multiple steps, return a JSON object with a "plan" key containing a list of steps.
Each step must have:
- "id": integer step ID (starting from 1)
- "action": one of [inform_user, search_web, rag_query, read_file, write_file, append_file, generate_content, summarize, embed_document, store_memory, reply_user]
- "params": dictionary of parameters for the action
- "description": brief description of what this step does

Example Multi-step Plan:
{
  "mode": "multi_step",
  "plan": [
    {
      "id": 1,
      "action": "search_web",
      "params": {"query": "latest AI news"},
      "description": "Search for latest AI news"
    },
    {
      "id": 2,
      "action": "summarize",
      "params": {"text": "$step_1_result"},
      "description": "Summarize the search results"
    },
    {
      "id": 3,
      "action": "reply_user",
      "params": {"message": "$step_2_result"},
      "description": "Send summary to user"
    }
  ]
}

Supported Actions & Params:
- inform_user(message: str): Send an intermediate update to the user.
- search_web(query: str): Search the internet.
- rag_query(query: str): Search uploaded documents/memory.
- read_file(path: str): Read a local file. (Use 'data/user_files/filename')
- write_file(path: str, content: str): Write to a file. (ALWAYS use 'data/user_files/filename')
- append_file(path: str, content: str): Append to a file. (Use 'data/user_files/filename')
- generate_content(prompt: str, context: str): Generate text using LLM.
- summarize(text: str): Summarize text.
- embed_document(path: str): Process and embed a file.
- store_memory(content: str): Save to long-term memory.
- reply_user(message: str): Final response to the user.
- disk_maintenance(): Check and prune disk usage.
- check_ingest_state(): Check if file ingestion is active.

CRITICAL: Output ONLY valid JSON. No markdown formatting, no explanations.
Files MUST be saved in 'data/user_files/'. Example: "data/user_files/notes.txt".

If the RAG system is currently ingesting a file (system flag: is_ingesting=True), your plan must first inform the user that the system is still processing a file and cannot answer RAG-based questions yet. Return a single 'inform_user' action in that case."""

class Planner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, user_input: str, context: str = "") -> Dict[str, Any]:
        """
        Generates a plan based on user input.
        Uses a strictly isolated context to prevent hallucination.
        """
        # CRITICAL: Do not inject conversation history or tools here.
        # The planner should only see the current request and relevant RAG context.
        
        messages = [
            SystemMessage(content=PLANNER_SYSTEM_PROMPT),
            HumanMessage(content=f"Context (RAG/Memory):\n{context}\n\nUser Request: {user_input}")
        ]

        try:
            # We use the LLM instance passed in, but we ensure the call is isolated via the messages list.
            # If the LLM instance has bound tools, we might need to unbind them or use a raw invoke.
            # Assuming self.llm is a ChatModel, invoke(messages) is standard.
            
            # If self.llm is a bound agent, this might fail. We expect a raw ChatModel here.
            response = self.llm.invoke(messages)
            content = response.content
            
            # Clean up potential markdown code blocks
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()
                
            plan_data = json.loads(content)
            return plan_data
        except json.JSONDecodeError:
            print(f"❌ Planner failed to generate valid JSON. Raw output: {content}")
            return {"mode": "single_step"} # Fallback
        except Exception as e:
            print(f"❌ Planner error: {e}")
            return {"mode": "single_step"} # Fallback
