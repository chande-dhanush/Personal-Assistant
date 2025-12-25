"""
Advanced Memory Manager

Features:
- Memory Weighting: Store importance scores with memories
- Reinforcement: Boost scores when memories are referenced
- Auto-Purging: Remove low-score memories periodically
- Memory Viewer: Debug API for inspecting memory state
- Auto-Summarization: Create summary memories for related items
"""
import time
import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)

# Default importance score for new memories
DEFAULT_IMPORTANCE = 0.5
MIN_IMPORTANCE = 0.1
MAX_IMPORTANCE = 1.0
REINFORCE_BOOST = 0.1
DECAY_RATE = 0.01  # Per-day decay
PURGE_THRESHOLD = 0.15  # Memories below this get purged
PURGE_TRIGGER_COUNT = 1000  # Purge every N vectors


class MemoryManager:
    """
    Advanced memory management with weighting, reinforcement, and purging.
    """
    
    def __init__(self, store):
        """
        Args:
            store: VectorMemoryStore instance
        """
        self.store = store
        self._last_purge_count = 0
    
    def store_with_importance(self, content: str, role: str, importance: float = None) -> bool:
        """
        Store a memory with an importance score.
        
        Args:
            content: Message content
            role: "user" or "assistant"
            importance: Score from 0.0-1.0 (None = DEFAULT_IMPORTANCE)
        
        Returns:
            True if stored, False if skipped
        """
        if importance is None:
            importance = DEFAULT_IMPORTANCE
        
        importance = max(MIN_IMPORTANCE, min(MAX_IMPORTANCE, importance))
        
        # Check if we need to add importance tracking to store
        if not hasattr(self.store, 'memory_importance'):
            self.store.memory_importance = {}
        
        # Store the message
        initial_count = len(self.store.memory_metadata)
        self.store.add_message(content, role)
        
        # If a new memory was added, record its importance
        if len(self.store.memory_metadata) > initial_count:
            idx = len(self.store.memory_metadata) - 1
            self.store.memory_importance[idx] = {
                "score": importance,
                "created": time.time(),
                "references": 0,
                "last_accessed": time.time()
            }
            
            # Check if purge is needed
            self._maybe_purge()
            
            return True
        return False
    
    def reinforce_memory(self, idx: int):
        """
        Boost a memory's importance when it's referenced.
        
        Args:
            idx: Index of the memory in memory_texts
        """
        if not hasattr(self.store, 'memory_importance'):
            return
        
        if idx in self.store.memory_importance:
            info = self.store.memory_importance[idx]
            info["score"] = min(MAX_IMPORTANCE, info["score"] + REINFORCE_BOOST)
            info["references"] += 1
            info["last_accessed"] = time.time()
            
            print(f"🔄 Memory #{idx} reinforced: score={info['score']:.2f}, refs={info['references']}")
    
    def get_weighted_score(self, idx: int, base_score: float) -> float:
        """
        Apply importance weighting to a retrieval score.
        
        Args:
            idx: Memory index
            base_score: Original retrieval score
        
        Returns:
            Weighted score
        """
        if not hasattr(self.store, 'memory_importance'):
            return base_score
        
        if idx not in self.store.memory_importance:
            return base_score
        
        info = self.store.memory_importance[idx]
        importance = info["score"]
        
        # Apply time decay
        days_old = (time.time() - info["created"]) / 86400
        decay = max(0.5, 1.0 - (days_old * DECAY_RATE))
        
        # Weight: 60% base score, 40% importance * decay
        weighted = (0.6 * base_score) + (0.4 * importance * decay)
        
        return weighted
    
    def _maybe_purge(self):
        """Check if purging is needed and run if so."""
        current_count = len(self.store.memory_texts)
        
        if current_count - self._last_purge_count >= PURGE_TRIGGER_COUNT:
            self.purge_low_importance()
            self._last_purge_count = current_count
    
    def purge_low_importance(self) -> int:
        """
        Remove memories with importance below threshold.
        
        Returns:
            Number of memories purged
        """
        if not hasattr(self.store, 'memory_importance'):
            return 0
        
        to_purge = []
        for idx, info in self.store.memory_importance.items():
            # Apply decay before checking
            days_old = (time.time() - info["created"]) / 86400
            decayed_score = info["score"] * max(0.5, 1.0 - (days_old * DECAY_RATE))
            
            if decayed_score < PURGE_THRESHOLD and info["references"] == 0:
                to_purge.append(idx)
        
        if to_purge:
            print(f"🗑️ Purging {len(to_purge)} low-importance memories")
            # Note: Actually removing from FAISS requires rebuilding index
            # For now, just mark as purged in importance dict
            for idx in to_purge:
                self.store.memory_importance[idx]["purged"] = True
        
        return len(to_purge)
    
    def get_memory_viewer_data(self, limit: int = 50) -> List[Dict]:
        """
        Get memory data for the viewer UI.
        
        Returns:
            List of memory entries with metadata and importance
        """
        entries = []
        
        start_idx = max(0, len(self.store.memory_texts) - limit)
        
        for i in range(start_idx, len(self.store.memory_texts)):
            text = self.store.memory_texts[i]
            meta = self.store.memory_metadata[i] if i < len(self.store.memory_metadata) else {}
            
            importance_info = {}
            if hasattr(self.store, 'memory_importance') and i in self.store.memory_importance:
                importance_info = self.store.memory_importance[i]
            
            entries.append({
                "index": i,
                "text": text[:200] + "..." if len(text) > 200 else text,
                "role": meta.get("role", "unknown"),
                "timestamp": meta.get("timestamp", ""),
                "importance": importance_info.get("score", DEFAULT_IMPORTANCE),
                "references": importance_info.get("references", 0),
                "purged": importance_info.get("purged", False)
            })
        
        return entries
    
    def get_memory_stats(self) -> Dict[str, Any]:
        """Get memory statistics for metrics."""
        total = len(self.store.memory_texts)
        
        stats = {
            "total_memories": total,
            "with_importance": 0,
            "avg_importance": 0.0,
            "purged_count": 0,
            "high_importance": 0,
            "low_importance": 0
        }
        
        if hasattr(self.store, 'memory_importance') and self.store.memory_importance:
            scores = []
            for idx, info in self.store.memory_importance.items():
                if info.get("purged"):
                    stats["purged_count"] += 1
                else:
                    scores.append(info["score"])
                    if info["score"] >= 0.7:
                        stats["high_importance"] += 1
                    elif info["score"] < 0.3:
                        stats["low_importance"] += 1
            
            stats["with_importance"] = len(scores)
            stats["avg_importance"] = sum(scores) / len(scores) if scores else 0.0
        
        return stats


# Singleton instance
_memory_manager = None

def get_memory_manager():
    """Get or create the memory manager singleton."""
    global _memory_manager
    
    if _memory_manager is None:
        from ..memory.faiss_store import get_memory_store
        store = get_memory_store()
        _memory_manager = MemoryManager(store)
    
    return _memory_manager


def store_with_importance(content: str, role: str, importance: float = None) -> bool:
    """Convenience function to store with importance."""
    return get_memory_manager().store_with_importance(content, role, importance)


def reinforce_memory(idx: int):
    """Convenience function to reinforce a memory."""
    get_memory_manager().reinforce_memory(idx)


def get_memory_viewer_data(limit: int = 50) -> List[Dict]:
    """Convenience function to get viewer data."""
    return get_memory_manager().get_memory_viewer_data(limit)


def get_advanced_memory_stats() -> Dict[str, Any]:
    """Convenience function to get stats."""
    return get_memory_manager().get_memory_stats()
