import os
import re
import time
from typing import List, Dict, Any, Optional

# LangChain & AI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage

# LangGraph (Modern Agent Replacement)
try:
    from langgraph.prebuilt import create_react_agent
except ImportError:
    print("❌ LangGraph not found. Please install langgraph.")
    create_react_agent = None

# Local Imports
from ..config import SYSTEM_PERSONALITY, GROQ_API_KEY, GOOGLE_API_KEY, USER_DETAILS
from .tools import get_all_tools, execute_actions
# ActionRouter is deprecated/removed, so we don't import it
from .note_routing import route_note_intent
from ..memory.faiss_store import get_relevant_context, add_message_to_memory
from ..utils.preferences import get_user_profile

# Hugging Face (Lazy Import)
try:
    from langchain_huggingface import HuggingFacePipeline
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

def sanitize_memory_text(text: str) -> str:
    """
    Sanitize text to prevent prompt injection.
    Strips control characters and system role mimicry.
    """
    if not text: return ""
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", text)
    text = re.sub(r"(?im)^(system|assistant|user|developer)\s*:", "Role:", text)
    return text.replace("---", "-").replace("===", "=")

class SmartAssistant:
    def __init__(self):
        self.tools = get_all_tools()
        self.available_models = [] # List of (name, llm_instance) tuples
        self.agent_cache = {} # Cache for LangGraph apps: {model_name: app}
        self._setup_llms()
        
    def _setup_llms(self):
        """Initialize ALL available LLMs for fallback strategy."""
        self.available_models = [] 
        
        # 1. Gemini (Primary)
        try:
            if GOOGLE_API_KEY:
                gemini = ChatGoogleGenerativeAI(
                    model="gemini-2.5-flash", 
                    temperature=0.3, # Lower temp for better tool use
                    google_api_key=GOOGLE_API_KEY,
                    max_retries=3,
                    request_timeout=30 # 30s timeout
                )
                self.available_models.append(("Gemini 2.5 Flash", gemini))
                print("✅ LLM Loaded: Gemini 2.5 Flash")
        except Exception as e:
            print(f"⚠️ Gemini init failed: {e}")
            
        # 2. Groq (Secondary)
        try:
            if GROQ_API_KEY:
                groq = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.3,
                    groq_api_key=GROQ_API_KEY,
                    max_retries=3,
                    request_timeout=30 # 30s timeout
                )
                self.available_models.append(("Groq Llama 3.3", groq))
                print("✅ LLM Loaded: Groq Llama 3.3")
        except Exception as e:
            print(f"⚠️ Groq init failed: {e}")

        # 3. Local Qwen (Fallback / Privacy)
        if HF_AVAILABLE:
            try:
                print("🔄 Loading Local Qwen 0.5B (CPU)...")
                # Use pipeline to auto-download/cache model
                local_llm = HuggingFacePipeline.from_model_id(
                    model_id="Qwen/Qwen2.5-0.5B-Instruct",
                    task="text-generation",
                    pipeline_kwargs={"max_new_tokens": 512, "do_sample": True, "temperature": 0.3},
                )
                self.available_models.append(("Local Qwen 0.5B", local_llm))
                print("✅ LLM Loaded: Local Qwen 0.5B")
            except Exception as e:
                print(f"⚠️ Local Qwen init failed: {e}")
        
        if not self.available_models:
            print("❌ CRITICAL: No LLMs available!")

    def _get_or_create_agent(self, model_name, llm):
        """Get cached agent or create new one for the specific model."""
        if model_name in self.agent_cache:
            return self.agent_cache[model_name]
            
        if not create_react_agent:
            return None
            
        try:
            agent = create_react_agent(llm, self.tools)
            self.agent_cache[model_name] = agent
            return agent
        except Exception as e:
            print(f"❌ Failed to create agent for {model_name}: {e}")
            return None

    def _validate_output(self, output: str) -> str:
        """
        Guardrail: Validates the final output from the LLM/Agent.
        """
        if not output or not output.strip():
            return "⚠️ The AI returned an empty response. Please try again."
        
        # Check for unparsed tool calls (hallucinations of tool execution)
        # e.g. "Action: spotify_control" appearing in the final text
        # We look for "Action:" at the start of a line to be safer
        if re.search(r"^Action:", output, re.MULTILINE):
             return f"⚠️ I tried to perform an action but couldn't execute it properly.\n\nRaw Output:\n{output}"
             
        return output

    def run(self, user_input: str, history: List[Dict]) -> str:
        """
        Unified Run Loop:
        1. Fast Path (Notes) - Optional
        2. Agent Loop (Tools + Chat)
        """
        if not self.available_models:
            return "❌ System Error: No AI models available."

        # 1. Get Context (RAG)
        context = get_relevant_context(user_input, max_chars=2000)
        safe_context = sanitize_memory_text(context)
        
        # 2. Fast Path: Note Intent (Optional - keep for speed if needed, or remove to fully unify)
        note_plan = route_note_intent(user_input)
        if note_plan:
            print(f"📝 Note Intent Detected: {note_plan}")
            try:
                # Execute directly
                result = execute_actions.invoke({"actions": [note_plan]})
                return f"✅ Note Action Executed:\n{result}"
            except Exception as e:
                print(f"⚠️ Note execution failed: {e}")

        # 3. Agent Execution (Unified Brain)
        messages = []
        user_profile = get_user_profile()
        
        # Optimized System Prompt for Chat
        full_system_prompt = (
            f"{SYSTEM_PERSONALITY}\n\n"
            f"=== USER PROFILE (Dynamic) ===\n{user_profile}\n\n"
            f"=== USER DETAILS (Fixed) ===\n{USER_DETAILS}\n\n"
            f"=== CONTEXT ===\n{safe_context}"
        )
        messages.append(SystemMessage(content=full_system_prompt))
        
        # History
        for msg in history[-4:]: # Keep history short for speed
            if msg['role'] == 'user':
                messages.append(HumanMessage(content=msg['content']))
            else:
                messages.append(AIMessage(content=msg['content']))
        
        # Final Input
        messages.append(HumanMessage(content=user_input))
        for model_name, llm in self.available_models:
            print(f"🤖 Generating response with: {model_name}...")
            
            try:
                # Use the React Agent for EVERYTHING
                agent = self._get_or_create_agent(model_name, llm)
                if agent:
                    result = agent.invoke({"messages": messages})
                    final_msg = result["messages"][-1]
                    final_content = final_msg.content
                    
                    # Handle list-based content (e.g. Anthropic/OpenAI structured output)
                    if isinstance(final_content, list):
                        text_parts = []
                        for part in final_content:
                            if isinstance(part, dict) and part.get('type') == 'text':
                                text_parts.append(part.get('text', ''))
                            elif isinstance(part, str):
                                text_parts.append(part)
                        final_content = "\n".join(text_parts)
                    
                    return self._validate_output(str(final_content))
                else:
                    # Fallback to raw LLM if agent creation fails
                    response = llm.invoke(messages)
                    return self._validate_output(str(response.content))
                
            except Exception as e:
                error_msg = str(e)
                print(f"⚠️ Error with {model_name}: {error_msg}")
                last_error = error_msg
                continue

        return f"❌ All models failed. Last error: {last_error}"

# Global instance
_assistant = None

def run_agentic_response(user_input: str, history: List[Dict]) -> str:
    global _assistant
    if not _assistant:
        _assistant = SmartAssistant()
    return _assistant.run(user_input, history)