import os
import shutil
import time
from pathlib import Path
from typing import Dict, Any
from ..memory.faiss_store.store import (
    DATA_DIR, BACKUP_DIR, 
    MEMORY_METADATA_FILE, FAISS_INDEX_PATH, 
    get_memory_store, write_memory_atomic
)

MAX_MEMORIES = 5000  # Soft limit for pruning
BACKUP_RETENTION_DAYS = 7

class MemoryMaintenance:
    """
    Handles system health, pruning, and backups.
    """
    def __init__(self):
        pass

    def run_startup_checks(self) -> Dict[str, Any]:
        """
        Run all maintenance tasks on startup.
        Returns a report dict.
        """
        report = {
            "pruned_memories": 0,
            "pruned_backups": 0,
            "errors": []
        }
        
        try:
            # 1. Prune Backups
            report["pruned_backups"] = self._prune_old_backups()
            
            # 2. Check Memory Size & Prune if needed
            store = get_memory_store()
            if store.faiss_index and store.faiss_index.ntotal > MAX_MEMORIES:
                report["pruned_memories"] = self._prune_excess_memories()
                
        except Exception as e:
            report["errors"].append(str(e))
            
        return report

    def _prune_old_backups(self) -> int:
        """Delete backups older than retention period."""
        count = 0
        now = time.time()
        retention_seconds = BACKUP_RETENTION_DAYS * 86400
        
        if not BACKUP_DIR.exists():
            return 0
            
        for backup_file in BACKUP_DIR.glob("*.bak"):
            try:
                if now - backup_file.stat().st_mtime > retention_seconds:
                    backup_file.unlink()
                    count += 1
            except Exception:
                pass
        return count

    def _prune_excess_memories(self) -> int:
        """
        Prune oldest memories to stay within limits.
        Note: Rebuilding FAISS index is required to delete vectors properly.
        """
        store = get_memory_store()
        current_count = len(store.memory_texts)
        if current_count <= MAX_MEMORIES:
            return 0
            
        to_remove = current_count - MAX_MEMORIES
        print(f"🧹 Pruning {to_remove} old memories...")
        
        # Keep the newest MAX_MEMORIES
        # Assuming memory_texts is append-only (oldest first)
        # We slice from [to_remove:]
        
        new_texts = store.memory_texts[to_remove:]
        new_metadata = store.memory_metadata[to_remove:]
        
        # Rebuild Index
        # This is expensive but necessary for clean pruning in simple FAISS
        # For larger systems, we'd use ID-based removal, but IndexFlatL2 doesn't support it easily without IDMap
        
        store.memory_texts = new_texts
        store.memory_metadata = new_metadata
        
        # Re-create index from scratch with new texts
        # Note: This requires re-embedding if we don't have vectors stored separately.
        # Since we don't store raw vectors on disk (only in FAISS bin), and FAISS write/read is opaque,
        # we might lose vectors if we just slice texts.
        
        # BETTER APPROACH for this architecture:
        # 1. Create new empty index
        # 2. Re-embed all kept texts (Expensive but safe)
        # OR
        # 3. If we had IDMap, we could remove.
        
        # Given we are using 'all-MiniLM-L6-v2' (fast), re-embedding 5000 items is acceptable on startup.
        
        store._create_new_index() # Clears index
        
        # Re-add all (Batching would be better, but simple loop for now)
        # We can access the embedding model from store
        if store.embeddings_model:
            embeddings = store.embeddings_model.encode(new_texts)
            import numpy as np
            store.faiss_index.add(np.array(embeddings, dtype=np.float32))
            
        # Save
        store._save_index()
        
        # Re-build inverted index
        store.inverted_index = {}
        for idx, text in enumerate(new_texts):
            store._update_inverted_index(text, idx)
            
        return to_remove

# Global Instance
maintenance_worker = MemoryMaintenance()

def run_maintenance():
    return maintenance_worker.run_startup_checks()
