import re
import hashlib
import uuid
from typing import List, Dict, Any

def split_sentences(text: str) -> List[str]:
    # Robust regex split
    return re.split(r'(?<=[.?!])\s+', text)

def chunk_text_semantics(text: str, metadata: Dict = None) -> List[Dict]:
    """
    Simple sliding window chunker.
    Future: Use embeddings for semantic boundaries.
    """
    sentences = split_sentences(text)
    chunks = []
    current_chunk = []
    current_len = 0
    max_len = 500 # chars approx
    
    for sent in sentences:
        if current_len + len(sent) > max_len and current_chunk:
            # Finalize
            chunk_text = " ".join(current_chunk)
            chunks.append({
                "id": str(uuid.uuid4()),
                "text": chunk_text,
                "metadata": metadata.copy() if metadata else {}
            })
            current_chunk = []
            current_len = 0
            
        current_chunk.append(sent)
        current_len += len(sent)
        
    if current_chunk:
        chunk_text = " ".join(current_chunk)
        chunks.append({
            "id": str(uuid.uuid4()),
            "text": chunk_text,
            "metadata": metadata.copy() if metadata else {}
        })
        
    return chunks
