import os
import re
import time
import threading
import gc
from typing import List, Dict, Any, Optional

from ..core.reflection import reflection_engine
from ..core.context_manager import get_smart_context
# LangChain & AI
from langchain_groq import ChatGroq
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks import StdOutCallbackHandler

# Local Imports
from ..config import (
    SYSTEM_PERSONALITY, GROQ_API_KEY, GOOGLE_API_KEY, USER_DETAILS, TOOL_BEHAVIOR_RULES,
    HISTORY_WINDOW, TOKEN_BUDGET, MIN_HISTORY,
    ENABLE_V4_SUMMARY, ENABLE_V4_COMPACT_CONTEXT, ENABLE_LOCAL_ROUTER,
    V4_MAX_RAW_MESSAGES, V4_MEMORY_LIMIT, V4_MEMORY_CHAR_LIMIT
)
from .tools import get_all_tools, execute_actions
# from .note_routing import route_note_intent

# from .relevance_mapper import get_tool_relevance # DEPRECATED
from .planner import Planner # NEW
from ..memory.faiss_store import get_relevant_context, get_memory_store

from ..utils.memory import cleanup_memory

# V4 Feature Imports
from ..utils.user_state import get_current_user_state, update_user_state
from ..utils.study_mode import detect_study_mode, get_study_mode_system_prompt, build_study_mode_response

# --- Qwen / Fallback Utils ---
# (Kept for emergency offline support, though user prefers Groq)
try:
    from transformers import AutoModelForCausalLM, AutoTokenizer
    HF_AVAILABLE = True
except ImportError:
    HF_AVAILABLE = False

_qwen_model = None
_qwen_tokenizer = None
_qwen_last_used = 0
_qwen_lock = threading.Lock()
IDLE_THRESHOLD = 600

def _load_qwen():
    """Lazy loads Qwen 0.5B on CPU."""
    global _qwen_model, _qwen_tokenizer, _qwen_last_used
    with _qwen_lock:
        if _qwen_model is None:
            if not HF_AVAILABLE:
                return None, None
            print("🧠 Loading Qwen 0.5B Fallback (CPU)...")
            try:
                _qwen_tokenizer = AutoTokenizer.from_pretrained("Qwen/Qwen2.5-0.5B-Instruct")
                _qwen_model = AutoModelForCausalLM.from_pretrained(
                    "Qwen/Qwen2.5-0.5B-Instruct", 
                    device_map="cpu"
                )
                print("✅ Qwen Loaded")
            except Exception as e:
                print(f"❌ Failed to load Qwen: {e}")
                return None, None
        _qwen_last_used = time.time()
        return _qwen_tokenizer, _qwen_model

def _unload_qwen_if_idle():
    global _qwen_model, _qwen_tokenizer
    while True:

        time.sleep(60)
        with _qwen_lock:
            if _qwen_model is not None:
                if time.time() - _qwen_last_used > IDLE_THRESHOLD:
                    print("💤 Unloaded Qwen.")
                    _qwen_model = None
                    _qwen_tokenizer = None
                    cleanup_memory()

threading.Thread(target=_unload_qwen_if_idle, daemon=True).start()

def sanitize_memory_text(text: str) -> str:
    if not text: return ""
    text = re.sub(r"[^\x09\x0A\x0D\x20-\x7E]", "", text)
    text = re.sub(r"(?im)^(system|assistant|user|developer)\s*:", "Role:", text)
    return text.replace("---", "-").replace("===", "=")

# Responder guardrail: Text-only output rule
RESPONDER_NO_TOOLS_RULE = """CRITICAL RULE: You are a TEXT-ONLY responder. You CANNOT call tools.
You must ONLY return plain text responses. Never output JSON, tool schemas, or {"name": ...} patterns.
If you believe a tool is needed, explain in plain text what action the user should take instead.
IMPORTANT: If tool outputs are provided below, the action was ALREADY completed. Acknowledge it naturally (e.g., "Playing now" or "Done") - do NOT tell the user to manually do it."""

def validate_responder_output(text: str) -> tuple[str, bool]:
    """
    Validate responder output and strip any tool-call patterns.
    Returns: (cleaned_text, had_violation)
    """
    # Detect tool-call JSON patterns
    tool_patterns = [
        r'\{\s*"name"\s*:', 
        r'\{\s*"tool"\s*:',
        r'\{\s*"function"\s*:',
        r'\{\s*"action"\s*:\s*"',
    ]
    
    had_violation = False
    for pattern in tool_patterns:
        if re.search(pattern, text, re.IGNORECASE):
            had_violation = True
            break
    
    if had_violation:
        # Log violation
        print("⚠️ [GUARDRAIL] Responder attempted tool call - stripping JSON")
        # Try to extract any plain text before the JSON
        clean = re.split(r'\{\s*"(name|tool|function|action)"\s*:', text)[0].strip()
        if not clean or len(clean) < 10:
            clean = "I apologize, but I encountered an issue processing that request. Could you please rephrase?"
        return clean, True
    
    return text, False

# LLM call timeout (seconds)
LLM_TIMEOUT = 60

import concurrent.futures

def invoke_with_timeout(llm, messages, timeout=LLM_TIMEOUT, **kwargs):
    """
    Invoke LLM with a timeout to prevent hanging after idle.
    Returns response or raises TimeoutError.
    """
    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
        future = executor.submit(llm.invoke, messages, **kwargs)
        try:
            return future.result(timeout=timeout)
        except concurrent.futures.TimeoutError:
            print(f"❌ [TIMEOUT] LLM call timed out after {timeout}s")
            raise TimeoutError(f"LLM call timed out after {timeout}s")

class ReliableLLM:
    """
    A wrapper that tries a Primary LLM, and falls back to a Backup LLM on error.
    Implements the standard LangChain 'invoke' interface with timeout protection.
    """
    def __init__(self, primary, backup=None, name="Model"):
        self.primary = primary
        self.backup = backup
        self.name = name
    
    def invoke(self, messages, timeout=LLM_TIMEOUT, **kwargs):
        print(f"🔄 [{self.name}] Invoking LLM...")
        try:
            result = invoke_with_timeout(self.primary, messages, timeout=timeout, **kwargs)
            print(f"✅ [{self.name}] LLM call succeeded")
            return result
        except (TimeoutError, Exception) as e:
            if self.backup:
                print(f"⚠️ {self.name} Primary failed: {e}. Switching to Backup (Gemini)...")
                try:
                    return invoke_with_timeout(self.backup, messages, timeout=timeout, **kwargs)
                except Exception as backup_err:
                    print(f"❌ {self.name} Backup also failed: {backup_err}")
                    raise backup_err
            print(f"❌ {self.name} Failed (No Backup Available): {e}")
            raise e

class SmartAssistant:

    def __init__(self):
        self.tools = get_all_tools()
        self.tool_map = {t.name: t for t in self.tools}
        self.current_mood = "Neutral"
        self._setup_llms()
        self.planner = Planner(self.planner_llm) if self.planner_llm else None

    def _setup_llms(self):
        """Initialize Tiered Models with Hot Failover."""
        self.intent_llm = None
        self.planner_llm = None
        self.responder_llm = None
        
        # 1. Initialize Backup (Gemini) ALWAYS (if key exists)
        gemini_backup = None
        if GOOGLE_API_KEY:
            try:
                gemini_backup = ChatGoogleGenerativeAI(
                    model="gemini-2.0-flash", 
                    temperature=0.3,
                    google_api_key=GOOGLE_API_KEY,
                    max_retries=2,
                    request_timeout=20
                )
                print("✅ Backup Model (Gemini) Loaded.")
            except Exception as e:
                print(f"⚠️ Gemini init failed: {e}")

        # 2. Initialize Primary (Groq)
        if GROQ_API_KEY:
            try:
                # -- Intent Router --
                groq_intent = ChatGroq(
                    model="llama-3.3-70b-versatile",
                    temperature=0.0,
                    groq_api_key=GROQ_API_KEY,
                    max_retries=1 # Fail fast to switch to backup
                )
                self.intent_llm = ReliableLLM(groq_intent, gemini_backup, "IntentRouter")

                # -- Planner --
                groq_planner = ChatGroq(
                    model="openai/gpt-oss-120b", 
                    temperature=0.1,
                    groq_api_key=GROQ_API_KEY,
                    max_retries=1
                )
                self.planner_llm = ReliableLLM(groq_planner, gemini_backup, "Planner")

                # -- Responder --
                groq_responder = ChatGroq(
                    model="openai/gpt-oss-20b",
                    temperature=0.7,
                    groq_api_key=GROQ_API_KEY,
                    max_retries=1
                )
                self.responder_llm = ReliableLLM(groq_responder, gemini_backup, "Responder")
                
                print("✅ Tiered Architecture Loaded (Groq + Gemini Failover).")
            except Exception as e:
                print(f"⚠️ Groq init failed: {e}")

        # 3. Fallback: If Groq failed completely, use Gemini as Primary
        if not self.intent_llm and gemini_backup:
            self.intent_llm = gemini_backup
            self.planner_llm = gemini_backup
            self.responder_llm = gemini_backup
            print("⚠️ Running on Gemini Backup (Groq Unavailable).")

    def _route_with_qwen(self, user_input: str) -> bool:
        """
        V4: Use Qwen 0.5B locally for routing (0 API tokens).
        Returns True if complex (needs tools), False if simple.
        """
        try:
            model, tokenizer = _load_qwen()
            if not model or not tokenizer:
                return False  # Default to simple if Qwen unavailable
            
            prompt = f"Classify this message as SIMPLE or COMPLEX. SIMPLE = casual chat. COMPLEX = needs tools like search, spotify, calendar, files. Reply with one word only.\n\nMessage: {user_input}\n\nClassification:"
            
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=128)
            outputs = model.generate(
                inputs.input_ids,
                max_new_tokens=5,
                temperature=0.1,
                do_sample=False,
                pad_token_id=tokenizer.eos_token_id
            )
            
            result = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True).lower().strip()
            return "complex" in result
            
        except Exception as e:
            print(f"⚠️ Qwen routing failed: {e}")
            return False  # Default to simple


    def run(self, user_input: str, history: List[Dict]) -> Dict[str, Any]:
        """
        ═══════════════════════════════════════════════════════════════
        FROZEN PIPELINE ARCHITECTURE - DO NOT MODIFY
        ═══════════════════════════════════════════════════════════════
        
        ROUTER (intent_llm)
            │
            ├─► SIMPLE → RESPONDER (text-only)
            │
            └─► COMPLEX → PLANNER → EXECUTOR → RESPONDER (text-only)
        
        RULES:
        - Router: Classifies SIMPLE/COMPLEX only, no tool calls
        - Planner: ONLY model allowed to emit tool JSON
        - Executor: Runs tools, outputs plain text
        - Responder: Text-only, tool_choice=none, validated output
        
        CONTEXT (single path):
        - Rolling summary (if history > 3)
        - Last 3 messages
        - Top 2 memories
        ═══════════════════════════════════════════════════════════════
        """
        print(f"🚀 [LLM] SmartAssistant.run() STARTED")
        start_time = time.time()
        
        # Default error response
        error_response = {
            "content": "I encountered an error. Please try again.",
            "metadata": {"mode": "Error", "tool_used": "None", "latency": "0s"}
        }
        
        try:
            # V4: Detect study mode FIRST (before any memory ops)
            study_mode_active = detect_study_mode(user_input)
            if study_mode_active:
                print(f"📚 Study Mode: ACTIVATED - Memory injection disabled")
            
            # V4.2: Import optimization config
            from ..config import (
                RAG_CONTEXT_MAX_CHARS, TOOL_OUTPUT_MAX_CHARS, 
                EXECUTOR_MAX_ITERATIONS, ENABLE_PLANNER_CACHE
            )
            
            # 2. Intent & Planning
            tool_outputs = ""
            tool_used = "None"
            mode = "Chat"
            safe_context = ""  # V4.2: Default empty, only fetch for COMPLEX
            
            # ═══ STEP 1: ROUTER (text-only classification) ═══
            # V4.2: Route FIRST, then decide if RAG is needed
            is_complex = False
            try:
                # Study mode always requires COMPLEX path
                if study_mode_active:
                    is_complex = True
                elif ENABLE_LOCAL_ROUTER:
                    # V4: Use Qwen locally for routing (0 API tokens)
                    is_complex = self._route_with_qwen(user_input)
                elif self.intent_llm:
                    # API router: text-only classification, no tools
                    router_msg = [
                        SystemMessage(content="Classify: SIMPLE (chat only) or COMPLEX (needs tools like Spotify, YouTube, Gmail, Calendar, web search). Reply with one word only. Never output JSON."),
                        HumanMessage(content=user_input)
                    ]
                    router_res = self.intent_llm.invoke(router_msg).content.lower()
                    is_complex = "complex" in router_res
                print(f"🚦 Router: {'COMPLEX' if is_complex else 'SIMPLE'}{' (Study Mode)' if study_mode_active else ''}")
            except Exception as e:
                print(f"⚠️ Router error: {e}")
                is_complex = False  # Default to simple on error
            
            # V4.2: RAG only for COMPLEX queries (skip for SIMPLE = major API/token savings)
            if is_complex and not study_mode_active:
                print(f"📚 [RAG] Fetching context...")
                try:
                    with concurrent.futures.ThreadPoolExecutor(max_workers=1) as executor:
                        future = executor.submit(get_relevant_context, user_input, RAG_CONTEXT_MAX_CHARS)
                        context = future.result(timeout=30)
                    # V4.2: Enforce max context size
                    if len(context) > RAG_CONTEXT_MAX_CHARS:
                        context = context[:RAG_CONTEXT_MAX_CHARS] + "..."
                    print(f"📚 [RAG] Context retrieved ({len(context)} chars)")
                    safe_context = sanitize_memory_text(context)
                except concurrent.futures.TimeoutError:
                    print(f"⚠️ [RAG] Context retrieval timed out - continuing without context")
                except Exception as e:
                    print(f"⚠️ [RAG] Context retrieval failed: {e}")
            elif not is_complex:
                print(f"⚡ [RAG] Skipped - SIMPLE query (V4.2 optimization)")
            
            # ═══ STEP 2: PLANNER + EXECUTOR (only if COMPLEX) ═══
            if is_complex and self.planner:
                # Study mode: Force RAG tool usage
                if study_mode_active:
                    mode = "Study/Source"
                else:
                    mode = "Complex/Tool"
                print("⚙️ Entering Detailed Mode (Planner)...")
                
                # Generate Plan
                plan_data = self.planner.plan(user_input, safe_context)
                steps = plan_data.get("plan", [])
                
                if steps:
                    results = []
                    # V4.2: Hard cap on execution steps (failsafe)
                    steps = steps[:EXECUTOR_MAX_ITERATIONS]
                    if len(plan_data.get("plan", [])) > EXECUTOR_MAX_ITERATIONS:
                        print(f"⚠️ Executor: Capped at {EXECUTOR_MAX_ITERATIONS} steps (was {len(plan_data.get('plan', []))})")
                    
                    for step in steps:
                        tool_name = step.get("tool")
                        tool_args = step.get("args", {})
                        
                        if tool_name in self.tool_map:
                            print(f"▶️ Executing Step {step.get('id')}: {tool_name} {tool_args}")
                            try:
                                # Execute Tool
                                res = self.tool_map[tool_name].invoke(tool_args)
                                
                                # --- Smart RAG & Web Scrape Summarization ---
                                res, tool_used = self._handle_smart_summarization(tool_name, res, user_input, tool_used)
                                
                                # V4.2: Truncate tool output before adding to results
                                res_str = str(res)
                                if len(res_str) > TOOL_OUTPUT_MAX_CHARS:
                                    res_str = res_str[:TOOL_OUTPUT_MAX_CHARS] + "... [truncated]"
                                
                                results.append(f"Step {step.get('id')} ({tool_name}): {res_str}")
                                tool_used = tool_name
                            except Exception as e:
                                results.append(f"Step {step.get('id')} Error: {e}")

                        else:
                            results.append(f"Step {step.get('id')} Error: Tool '{tool_name}' not found.")
                    tool_outputs = "\n\n=== TOOL EXECUTION LOG ===\n" + "\n".join(results)

                else:
                    tool_outputs = "(No tools were deemed necessary by the planner)."

            # ═══ STEP 3: RESPONDER (text-only, ALWAYS runs) ═══
            print(f"🏁 [LLM] SmartAssistant.run() completing - calling responder")
            return self._generate_final_response(
                user_input, tool_outputs, history, safe_context, start_time, 
                tool_used, mode, study_mode_active
            )
            
        except Exception as e:
            print(f"❌ [LLM] SmartAssistant.run() FATAL ERROR: {e}")
            import traceback
            traceback.print_exc()
            error_response["content"] = f"I encountered an error: {str(e)[:100]}. Please try again."
            error_response["metadata"]["latency"] = f"{time.time() - start_time:.2f}s"
            return error_response


    def _handle_smart_summarization(self, tool_name: str, res: Any, user_input: str, current_tool_used: str):
        """
        Helper: Post-processes RAG/Web outputs with GPT-120b.
        Includes Adaptive Retry loop.
        """
        is_rag = tool_name == "fetch_document_context"
        is_scrape = tool_name == "web_scrape"
        
        if not (is_rag or is_scrape) or not self.planner_llm:
            return res, current_tool_used

        try:
            data_len = len(str(res))
            if data_len <= 500:
                return res, current_tool_used

            print(f"🧠 Smart Summary: Analyzing {data_len} chars with GPT-120b...")
            
            # Loop for Adaptive Retrieval (Max 1 retry)
            for attempt in range(2):
                system_content = "You are an expert researcher."
                if is_rag:
                    system_content += " Evaluate the RAG search results. 1. If irrelevant, reply 'RETRY: <better_query>'. 2. Else, summarize concisely."
                else:
                    system_content += " Summarize the following website content. Focus on the main topic and key details. Ignore navigation menus or footer text."

                rag_prompt = [
                    SystemMessage(content=system_content),
                    HumanMessage(content=f"User Query: {user_input}\n\nRaw Data:\n{res}")
                ]

                try:
                    summary_res = self.planner_llm.invoke(rag_prompt).content
                    
                    if summary_res.startswith("RETRY:") and attempt == 0:
                        new_query = summary_res.replace("RETRY:", "").strip()
                        print(f"🔄 Adaptive RAG: Context poor. Retrying with query: '{new_query}'")
                        # Re-fetch with new query
                        res = self.tool_map[tool_name].invoke({"query": new_query})
                        continue 
                    else:
                        new_res = f"⚡ Smart Summary (GPT-120b):\n{summary_res}\n\n(Original Raw Data Hidden)"
                        return new_res, "SmartSummarizer"
                except Exception as e:
                    print(f"⚠️ Smart Sum/Retry failed: {e}")
                    break
                    
        except Exception as e:
            print(f"⚠️ Smart Handler Error: {e}")
            
        return res, current_tool_used

    def _generate_final_response(self, user_input, tool_outputs, history, safe_context, start_time, tool_used, mode, study_mode_active=False):
        """
        V4 Compact Token Pipeline:
        - System prompt (full personality)
        - Merged <CONTEXT> block (summary + 3 msgs + 2 memories)
        - Single HumanMessage(user_input)
        
        Target: ~500-900 tokens total
        """
        messages = []
        user_state = get_current_user_state()  # V4: Get user state for metadata
        
        # V4: Routines emit directly via ViewModel, NOT through responder
        # (morning_context removed - routines bypass LLM pipeline)
        
        # V4: Study mode additional instructions
        study_mode_prompt = ""
        if study_mode_active:
            study_mode_prompt = get_study_mode_system_prompt()

        # 1. SYSTEM PROMPT (full personality - kept as-is)
        # Include responder guardrail rule
        system_prompt = (
            f"{SYSTEM_PERSONALITY}\n"
            f"{RESPONDER_NO_TOOLS_RULE}\n"
            f"{study_mode_prompt}\n"  # V4: Study mode rules (empty if not active)
            f"CURRENT MOOD: {self.current_mood}\n"
            f"USER STATE: {user_state}\n"  # V4: User state awareness
            f"{tool_outputs if tool_outputs else ''}\n"
            f"Task: Respond naturally based on context."
        )
        messages.append(SystemMessage(content=system_prompt))
        
        # 2. V4 COMPACT CONTEXT (FROZEN - single path only)
        # Structure: summary + 3 recent + 2 memories
        compact_context = self._build_v4_context(history, safe_context, user_input)
        messages.append(SystemMessage(content=compact_context))
        
        # Token estimation
        est_tokens = len(compact_context) // 4
        print(f"📦 V4 Compact Context: {len(compact_context)} chars (~{est_tokens} tokens)")
        
        # 3. CURRENT USER INPUT (single message, no duplication)
        messages.append(HumanMessage(content=user_input))
        
        # 4. INVOKE RESPONDER (text-only, no tools allowed)
        final_response = "..."
        if self.responder_llm:
            try:
                total_msgs = len(messages)
                print(f"🤖 Synthesizing... ({total_msgs} messages)")
                
                # Guardrail: Invoke with tool_choice=none
                res = self.responder_llm.invoke(messages, tool_choice="none")
                raw_response = res.content
                
                # Guardrail: Validate and strip any tool-call patterns
                final_response, had_violation = validate_responder_output(raw_response)
                if had_violation:
                    from ..utils.stability_logger import log_warning
                    log_warning(f"Responder tool-call violation detected and stripped")
                    
            except Exception as e:
                # Check if error is about tool_choice parameter not being supported
                if "tool_choice" in str(e).lower():
                    print("⚠️ Model doesn't support tool_choice, retrying without...")
                    try:
                        res = self.responder_llm.invoke(messages)
                        raw_response = res.content
                        final_response, _ = validate_responder_output(raw_response)
                    except Exception as e2:
                        final_response = f"❌ Response Error: {e2}"
                else:
                    final_response = f"❌ Response Error: {e}"
        else:
            final_response = "❌ No Responder LLM available."

        return {
            "content": final_response,
            "metadata": {
                "mood": self.current_mood,
                "user_state": user_state,  # V4: User state awareness
                "tool_used": tool_used,
                "mode": mode,
                "study_mode": study_mode_active,  # V4: Study mode flag
                "latency": f"{time.time() - start_time:.2f}s",
                "v4_compact": ENABLE_V4_COMPACT_CONTEXT,
                "memory_chars": len(safe_context) if safe_context else 0
            }
        }
    
    def _build_v4_context(self, history: List[Dict], safe_context: str, user_input: str) -> str:
        """
        Build V4 merged compact context block.
        Target: 120-180 tokens
        """
        from ..utils.summary import update_rolling_summary, build_compact_context
        from ..utils.stability_logger import log_ctx
        
        # 1. Rolling Summary (update and get)
        rolling_summary = ""
        if ENABLE_V4_SUMMARY and len(history) > V4_MAX_RAW_MESSAGES:
            rolling_summary = update_rolling_summary(history)
        
        # 2. Recent Messages (last 3 only)
        recent_messages = history[-V4_MAX_RAW_MESSAGES:] if history else []
        
        # 3. Compact Memory Items (top 2 with importance)
        memory_items = self._get_compact_memories(user_input)
        
        # Log context stats
        log_ctx(len(rolling_summary), len(recent_messages), len(memory_items))
        
        # Build merged context
        return build_compact_context(rolling_summary, recent_messages, memory_items)
    
    def _get_compact_memories(self, query: str) -> List[Dict]:
        """Get top N memories with importance/relevance scores."""
        try:
            store = get_memory_store()
            
            if not store or not store.faiss_index or store.faiss_index.ntotal == 0:
                return []
            
            # Ensure embeddings loaded
            store._ensure_embeddings_loaded()
            if not store.embeddings_model:
                return []
            
            # Vector search
            query_embedding = store.embeddings_model.encode([query])[0]
            import numpy as np
            distances, indices = store.faiss_index.search(
                np.array([query_embedding], dtype=np.float32), 
                k=V4_MEMORY_LIMIT
            )
            
            results = []
            for i, idx in enumerate(indices[0]):
                if idx == -1 or idx >= len(store.memory_texts):
                    continue
                
                text = store.memory_texts[idx][:V4_MEMORY_CHAR_LIMIT]
                relevance = 1.0 / (1.0 + distances[0][i])
                
                # Get importance score
                importance = 0.5
                key = str(idx)
                if key in store.memory_importance:
                    importance = float(store.memory_importance[key])
                
                # Patch 2: Reinforce memory when retrieved (using store method)
                store.reinforce_memory(idx, boost=0.1)
                
                results.append({
                    "text": text,
                    "importance": importance,
                    "relevance": relevance,
                    "idx": idx
                })
            
            return results
            
        except Exception as e:
            print(f"⚠️ Memory retrieval error: {e}")
            return []

_assistant = None
def run_agentic_response(user_input: str, history: List[Dict]) -> Dict[str, Any]:
    global _assistant
    if not _assistant:
        _assistant = SmartAssistant()
    return _assistant.run(user_input, history)

