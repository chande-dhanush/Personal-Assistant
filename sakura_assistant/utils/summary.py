"""
V4 Rolling Conversation Summary

Maintains a compressed summary of conversation history to reduce token usage.
Uses Qwen 0.5B locally for summarization (0 API tokens).
"""
import logging
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

# Rolling summary state
_rolling_summary = ""
_turn_count = 0

SUMMARY_PROMPT = """Compress the following conversation into a 2-3 sentence summary. 
Focus on: user preferences, ongoing topics, key facts mentioned, emotional context.
Do not include greetings or trivial exchanges.

Conversation:
{history}

Summary:"""


def generate_summary(history_window: List[Dict]) -> str:
    """
    Generate a compressed summary of the conversation history.
    Uses fallback extractive summary when local models are disabled.
    """
    if not history_window:
        return ""
    
    # Format history for summarization
    formatted = "\n".join([
        f"{m.get('role', 'user').title()}: {m.get('content', '')[:200]}"
        for m in history_window[-10:]  # Summarize last 10 messages max
    ])
    
    # Check if local models are enabled
    from ..config import ENABLE_LOCAL_ROUTER
    if not ENABLE_LOCAL_ROUTER:
        # Skip Qwen, use fallback to avoid loading CPU model
        return _fallback_summary(history_window)
    
    # Try Qwen first (local, 0 API cost)
    try:
        from ..core.llm import _load_qwen
        
        model, tokenizer = _load_qwen()
        if model and tokenizer:
            prompt = SUMMARY_PROMPT.format(history=formatted)
            inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=512)
            
            outputs = model.generate(
                inputs.input_ids,
                max_new_tokens=100,
                temperature=0.3,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id
            )
            
            summary = tokenizer.decode(outputs[0][inputs.input_ids.shape[1]:], skip_special_tokens=True)
            logger.info(f"Generated summary via Qwen: {len(summary)} chars")
            return summary.strip()
    except Exception as e:
        logger.warning(f"Qwen summarization failed: {e}")
    
    # Fallback: Simple extractive summary (no LLM)
    return _fallback_summary(history_window)


def _fallback_summary(history_window: List[Dict]) -> str:
    """
    Fallback extractive summary when Qwen is unavailable.
    Extracts key phrases from recent messages.
    """
    key_phrases = []
    
    for msg in history_window[-8:]:
        content = msg.get('content', '')
        role = msg.get('role', 'user')
        
        # Skip very short messages
        if len(content) < 20:
            continue
        
        # Extract first sentence or first 100 chars
        first_sentence = content.split('.')[0][:100]
        if len(first_sentence) > 30:
            key_phrases.append(f"{role}: {first_sentence}")
    
    if key_phrases:
        return "Recent topics: " + "; ".join(key_phrases[-3:])
    return ""


def get_rolling_summary() -> str:
    """Get the current rolling summary."""
    global _rolling_summary
    return _rolling_summary


def update_rolling_summary(history: List[Dict], force: bool = False) -> str:
    """
    Update the rolling summary if enough turns have passed.
    
    Args:
        history: Full conversation history
        force: Force update regardless of turn count
    
    Returns:
        Current rolling summary
    """
    global _rolling_summary, _turn_count
    
    from ..config import V4_SUMMARY_INTERVAL, ENABLE_V4_SUMMARY
    
    if not ENABLE_V4_SUMMARY:
        return ""
    
    _turn_count += 1
    
    # Update every N turns or if forced
    if force or _turn_count >= V4_SUMMARY_INTERVAL:
        _turn_count = 0
        
        # Exclude last 3 messages (those will be sent raw)
        from ..config import V4_MAX_RAW_MESSAGES
        history_to_summarize = history[:-V4_MAX_RAW_MESSAGES] if len(history) > V4_MAX_RAW_MESSAGES else []
        
        if history_to_summarize:
            _rolling_summary = generate_summary(history_to_summarize)
            print(f"📝 Rolling summary updated: {len(_rolling_summary)} chars")
    
    return _rolling_summary


def reset_summary():
    """Reset the rolling summary (e.g., on new conversation)."""
    global _rolling_summary, _turn_count
    _rolling_summary = ""
    _turn_count = 0


def build_compact_context(
    rolling_summary: str,
    recent_messages: List[Dict],
    memory_items: List[Dict]
) -> str:
    """
    Build the merged V4 compact context block.
    
    Target: 120-180 tokens total.
    
    Args:
        rolling_summary: The compressed conversation summary
        recent_messages: Last 3 raw messages
        memory_items: Top 2 memory items with scores
    
    Returns:
        Formatted <CONTEXT> block
    """
    parts = ["<CONTEXT>"]
    
    # Summary block
    if rolling_summary:
        parts.append(f"Summary:\n{rolling_summary[:400]}")  # Cap at 400 chars
    
    # Recent messages (last 3)
    if recent_messages:
        recent_lines = []
        for msg in recent_messages[-3:]:
            role = msg.get('role', 'user')[0].upper()  # U or A
            content = msg.get('content', '')[:150]  # Truncate
            recent_lines.append(f"- [{role}] {content}")
        parts.append("Recent:\n" + "\n".join(recent_lines))
    
    # Memory items (top 2)
    if memory_items:
        memory_lines = []
        for mem in memory_items[:2]:
            text = mem.get('text', '')[:140]
            imp = mem.get('importance', 0.5)
            rel = mem.get('relevance', 0.5)
            memory_lines.append(f'- "{text}" (imp={imp:.2f}, rel={rel:.2f})')
        parts.append("Memory:\n" + "\n".join(memory_lines))
    
    parts.append("</CONTEXT>")
    
    return "\n\n".join(parts)
