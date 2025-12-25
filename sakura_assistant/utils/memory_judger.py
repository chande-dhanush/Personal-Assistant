"""
LLM-based Memory Importance Classifier

Decides per-message whether content should be stored in long-term FAISS memory.
Replaces brittle heuristic filters with intelligent classification.
Returns importance scores for memory weighting.
"""
import logging
import re
from typing import Tuple

logger = logging.getLogger(__name__)

# Lazy-loaded LLM
_memory_judger_llm = None

MEMORY_JUDGER_PROMPT = """You are a memory classifier for a personal AI assistant. Decide whether the following message should be added to long-term memory.

Criteria for "YES" (include importance 1-10):
- personal preferences (likes, dislikes, favorites) - HIGH importance (8-10)
- biographical info (name, age, location, birthday) - HIGH importance (9-10)
- goals, plans, intentions - HIGH importance (7-9)
- emotional disclosures - MEDIUM importance (6-8)
- meaningful opinions - MEDIUM importance (5-7)
- project- or work-related information - HIGH importance (8-10)
- technical debugging context - MEDIUM importance (5-7)
- repeated issues or patterns - MEDIUM importance (6-8)

Criteria for "NO":
- greetings or small talk ("hi", "thanks")
- acknowledgements ("ok", "lol", "sure", "got it")
- short-lived ephemeral commands
- tool usage messages or logs
- accidental noise or empty content
- single word responses

Respond ONLY with:
"yes [importance 1-10] - <short reason>"
or
"no - <short reason>"

Example: "yes [8] - personal preference about anime"
"""

def _get_judger_llm():
    """Lazy-load the memory judger LLM."""
    global _memory_judger_llm
    
    if _memory_judger_llm is not None:
        return _memory_judger_llm
    
    from ..config import MEMORY_JUDGER_MODEL, GROQ_API_KEY
    
    if not GROQ_API_KEY:
        logger.warning("No GROQ_API_KEY, memory judger disabled")
        return None
    
    try:
        from langchain_groq import ChatGroq
        _memory_judger_llm = ChatGroq(
            model=MEMORY_JUDGER_MODEL,
            temperature=0,
            max_tokens=64,  # Very short response needed
            groq_api_key=GROQ_API_KEY
        )
        logger.info(f"Memory Judger LLM loaded: {MEMORY_JUDGER_MODEL}")
        return _memory_judger_llm
    except Exception as e:
        logger.error(f"Failed to load memory judger: {e}")
        return None


def should_store_message(text: str, role: str = "user") -> Tuple[bool, str, float]:
    """
    Use LLM to decide if a message should be stored in long-term memory.
    
    Args:
        text: The message content
        role: "user" or "assistant"
    
    Returns:
        (should_store: bool, reason: str, importance: float 0.0-1.0)
    """
    from ..config import USE_MEMORY_JUDGER
    
    # Quick filters (keep these for efficiency)
    if not text or len(text.strip()) < 5:
        return False, "too short", 0.0
    
    if "TOOL EXECUTION LOG" in text or "[DEBUG]" in text:
        return False, "tool output", 0.0
    
    if not USE_MEMORY_JUDGER:
        # Fallback: store everything that passes basic filters with medium importance
        return True, "judger disabled", 0.5
    
    # Get LLM
    llm = _get_judger_llm()
    if llm is None:
        # No LLM available, use permissive fallback
        return len(text) > 20, "no judger LLM", 0.5
    
    try:
        from langchain_core.messages import SystemMessage, HumanMessage
        
        # Truncate to save tokens (first 500 chars is enough for classification)
        truncated = text[:500] if len(text) > 500 else text
        
        messages = [
            SystemMessage(content=MEMORY_JUDGER_PROMPT),
            HumanMessage(content=f"Role: {role}\nMessage:\n{truncated}")
        ]
        
        response = llm.invoke(messages).content.strip().lower()
        
        # Parse response
        should_store = response.startswith("yes")
        
        # Extract importance score from pattern like "yes [8] - reason"
        importance = 0.5  # default
        importance_match = re.search(r'\[(\d+)\]', response)
        if importance_match:
            raw_score = int(importance_match.group(1))
            importance = min(1.0, max(0.1, raw_score / 10.0))
        elif should_store:
            importance = 0.6  # Default for yes without score
        
        # Extract reason
        reason = response.split("-", 1)[1].strip() if "-" in response else response
        
        # Debug log
        decision = "✅ STORE" if should_store else "⏭️ SKIP"
        print(f"🧠 MemoryJudger: {decision} (imp={importance:.1f}) - {reason[:50]}")
        
        return should_store, reason, importance
        
    except Exception as e:
        logger.error(f"Memory judger error: {e}")
        # On error, be permissive for important-looking messages
        return len(text) > 50, f"error: {str(e)[:30]}", 0.5


def classify_message_importance(text: str) -> str:
    """
    Get importance classification without the store decision.
    Useful for debugging/metrics.
    """
    should_store, reason, importance = should_store_message(text)
    return f"{'important' if should_store else 'skip'} ({importance:.1f}): {reason}"


def get_importance_score(text: str, role: str = "user") -> float:
    """
    Get just the importance score for a message.
    """
    _, _, importance = should_store_message(text, role)
    return importance
