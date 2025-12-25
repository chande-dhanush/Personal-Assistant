"""
Knowledge / Study Mode - Source-Bound Answering.

Triggered by: "from the textbook", "according to the book", "use only the source"
Uses existing fetch_document_context tool.
Strict output format with source attribution.

Detection happens in Router (no pre-router branching).
Missing metadata = "Not specified". Low confidence = refuse.
"""

import re
from typing import Optional, Dict, Any, Tuple

from ..utils.stability_logger import log_flow

# Trigger phrases that activate study mode
STUDY_MODE_TRIGGERS = [
    r"from the textbook",
    r"according to the book",
    r"refer and answer",
    r"use only the source",
    r"based on the document",
    r"from the uploaded",
    r"from my notes",
    r"from the pdf",
    r"cite the source",
    r"answer from the file"
]

# Compiled regex for efficiency
_TRIGGER_PATTERN = re.compile(
    r'(' + '|'.join(STUDY_MODE_TRIGGERS) + r')',
    re.IGNORECASE
)

# Minimum confidence threshold for accepting an answer
MIN_CONFIDENCE_THRESHOLD = 0.4


def detect_study_mode(user_input: str) -> bool:
    """
    Check if user input contains study mode trigger phrases.
    Called from Router to determine if study_mode=True should be set.
    """
    is_study_mode = bool(_TRIGGER_PATTERN.search(user_input))
    
    if is_study_mode:
        log_flow("StudyMode", f"Activated by trigger in: '{user_input[:50]}...'")
    
    return is_study_mode


def format_study_response(
    answer: str,
    source_filename: str = None,
    section_page: str = None,
    excerpt: str = None,
    confidence: float = 0.0
) -> str:
    """
    Format response in strict study mode format.
    Missing fields show "Not specified" instead of guessing.
    """
    # Validate we have a source
    if not source_filename:
        source_filename = "Not specified"
    
    if not section_page:
        section_page = "Not specified"
    
    if not excerpt:
        excerpt = "Not available"
    
    return f"""**Answer:** {answer}

**Source:** {source_filename}
**Section/Page:** {section_page}
**Excerpt:** "{excerpt}"
"""


def validate_study_response(
    context_results: str,
    confidence: float
) -> Tuple[bool, str]:
    """
    Validate that we have sufficient context to answer in study mode.
    Returns (is_valid, refusal_reason_if_invalid)
    """
    # Check if we have any context
    if not context_results or context_results.strip() == "":
        return False, "I couldn't find any relevant information in your uploaded documents."
    
    if "No context found" in context_results or "No relevant documents" in context_results:
        return False, "I couldn't find that source. Please upload it first, then ask again."
    
    # Check confidence threshold
    if confidence < MIN_CONFIDENCE_THRESHOLD:
        return False, "The retrieved content doesn't seem relevant enough to answer confidently. Please try rephrasing your question or uploading the correct source."
    
    return True, ""


def extract_source_metadata(context: str) -> Dict[str, Any]:
    """
    Extract source metadata from RAG context string.
    Returns dict with filename, page, excerpt.
    """
    result = {
        "filename": None,
        "section_page": None,
        "excerpt": None,
        "confidence": 0.0
    }
    
    try:
        # Extract filename: **File**: filename (Pg X) pattern
        file_match = re.search(r'\*\*File\*\*:\s*([^\n|]+)', context)
        if file_match:
            result["filename"] = file_match.group(1).strip()
        
        # Extract page if present
        page_match = re.search(r'\(Pg\s*(\d+)\)', context)
        if page_match:
            result["section_page"] = f"Page {page_match.group(1)}"
        
        # Extract score as confidence
        score_match = re.search(r'\*\*Score\*\*:\s*([0-9.]+)', context)
        if score_match:
            result["confidence"] = float(score_match.group(1))
        
        # Extract first excerpt (content between > and ---)
        excerpt_match = re.search(r'>\s*(.+?)(?:\n---|\Z)', context, re.DOTALL)
        if excerpt_match:
            excerpt = excerpt_match.group(1).strip()
            # Limit excerpt length
            if len(excerpt) > 200:
                excerpt = excerpt[:200] + "..."
            result["excerpt"] = excerpt
    
    except Exception as e:
        log_flow("StudyMode", f"Metadata extraction failed: {e}")
    
    return result


def get_study_mode_system_prompt() -> str:
    """
    Get additional system prompt instructions for study mode.
    Appended to responder prompt when study mode is active.
    """
    return """
STUDY MODE ACTIVE: You MUST follow these rules strictly:
1. Answer ONLY from the provided source context.
2. Do NOT add information from your training data.
3. If the context doesn't contain the answer, say "The source doesn't contain this information."
4. Use the exact format: Answer, Source, Section/Page, Excerpt.
5. Quote the relevant passage in the Excerpt field.
6. Never hallucinate or guess content not in the source.
"""


def build_study_mode_response(
    query: str,
    context_results: str,
    generated_answer: str
) -> str:
    """
    Build final study mode response by combining answer with source metadata.
    """
    metadata = extract_source_metadata(context_results)
    
    # Validate we have sufficient data
    is_valid, refusal = validate_study_response(
        context_results, 
        metadata.get("confidence", 0.0)
    )
    
    if not is_valid:
        log_flow("StudyMode", f"Refused: {refusal}")
        return refusal
    
    return format_study_response(
        answer=generated_answer,
        source_filename=metadata.get("filename"),
        section_page=metadata.get("section_page"),
        excerpt=metadata.get("excerpt"),
        confidence=metadata.get("confidence", 0.0)
    )
