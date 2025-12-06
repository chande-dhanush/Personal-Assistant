import os
import shutil
import time
from typing import Dict, List, Any
# from ..utils.vectorstore import get_vectorstore, VECTOR_STORE_PATH
from ..utils.file_registry import get_file_registry

# Configuration
MAX_DISK_USAGE_GB = 1.0  # Set low for testing, maybe 1GB or 5GB in prod
WARNING_THRESHOLD = 0.8
PRUNE_THRESHOLD = 0.9

class DiskGuardian:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(DiskGuardian, cls).__new__(cls)
        return cls._instance

    def get_disk_usage(self) -> Dict[str, Any]:
        """
        Returns disk usage stats for the vectorstore directory.
        """
        # Stubbed out as vectorstore is removed
        return {
            "size_bytes": 0,
            "size_gb": 0,
            "usage_percent": 0,
            "warning": False,
            "critical": False
        }

    def check_and_prune(self) -> str:
        """
        Checks disk usage and auto-prunes if critical.
        Returns a status message.
        """
        return "✅ Disk usage check skipped (VectorStore removed)."

    def delete_orphaned_namespaces(self) -> str:
        """
        Deletes namespaces in VectorStore that are not in FileRegistry.
        """
        return "Orphan cleanup skipped."

# Global accessor
def get_disk_guardian():
    return DiskGuardian()
