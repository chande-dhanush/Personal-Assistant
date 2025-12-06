import sqlite3
import os
import json
import hashlib
from datetime import datetime
from typing import Dict, Any, Optional, List

DB_PATH = os.path.join(os.getcwd(), "data", "files.db")

class FileRegistry:
    def __init__(self):
        self._init_db()

    def _init_db(self):
        """Initialize SQLite database with updated schema."""
        os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Create table if not exists (base schema)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS files (
                file_id TEXT PRIMARY KEY,
                filename TEXT,
                file_type TEXT,
                added_at TEXT,
                chunk_count INTEGER,
                metadata TEXT
            )
        """)
        
        # Check for new columns and add them if missing
        cursor.execute("PRAGMA table_info(files)")
        columns = [info[1] for info in cursor.fetchall()]
        
        if "namespace" not in columns:
            print("🔄 Migrating DB: Adding 'namespace' column...")
            cursor.execute("ALTER TABLE files ADD COLUMN namespace TEXT")
            
        if "file_hash" not in columns:
            print("🔄 Migrating DB: Adding 'file_hash' column...")
            cursor.execute("ALTER TABLE files ADD COLUMN file_hash TEXT")

        conn.commit()
        conn.close()

    def add_file(self, file_id: str, filename: str, file_type: str, chunk_count: int, metadata: Dict[str, Any]):
        """Register a new file with deduplication check."""
        # Calculate hash if source path exists
        source_path = metadata.get("source_path")
        file_hash = None
        if source_path and os.path.exists(source_path):
            file_hash = self._calculate_hash(source_path)
            
            # Dedupe check
            if self._file_exists_by_hash(file_hash):
                print(f"⚠️ File '{filename}' already exists (hash match). Skipping registration.")
                return

        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        namespace = metadata.get("namespace", file_id)
        
        cursor.execute("""
            INSERT INTO files (file_id, filename, file_type, added_at, chunk_count, metadata, namespace, file_hash)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            file_id,
            filename,
            file_type,
            datetime.now().isoformat(),
            chunk_count,
            json.dumps(metadata),
            namespace,
            file_hash
        ))
        conn.commit()
        conn.close()
        print(f"✅ Registered file: {filename} ({file_id})")

    def get_file(self, file_id: str) -> Optional[Dict[str, Any]]:
        """Get file details by ID."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE file_id = ?", (file_id,))
        row = cursor.fetchone()
        conn.close()
        return self._row_to_dict(row) if row else None

    def list_files(self) -> List[Dict[str, Any]]:
        """List all registered files."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files")
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def list_files_by_namespace(self, namespace: str) -> List[Dict[str, Any]]:
        """List files in a specific namespace."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM files WHERE namespace = ?", (namespace,))
        rows = cursor.fetchall()
        conn.close()
        return [self._row_to_dict(row) for row in rows]

    def delete_file(self, file_id: str):
        """Delete a file from registry and vectorstore."""
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM files WHERE file_id = ?", (file_id,))
        conn.commit()
        conn.close()
        print(f"🗑️ Unregistered file: {file_id}")

    def _calculate_hash(self, file_path: str) -> str:
        """Calculate SHA256 hash of a file."""
        sha256_hash = hashlib.sha256()
        try:
            with open(file_path, "rb") as f:
                for byte_block in iter(lambda: f.read(4096), b""):
                    sha256_hash.update(byte_block)
            return sha256_hash.hexdigest()
        except Exception as e:
            print(f"⚠️ Hash calc failed: {e}")
            return None

    def _file_exists_by_hash(self, file_hash: str) -> bool:
        """Check if file with same hash exists."""
        if not file_hash: return False
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("SELECT 1 FROM files WHERE file_hash = ?", (file_hash,))
        exists = cursor.fetchone() is not None
        conn.close()
        return exists

    def _row_to_dict(self, row) -> Dict[str, Any]:
        return {
            "file_id": row[0],
            "filename": row[1],
            "file_type": row[2],
            "added_at": row[3],
            "chunk_count": row[4],
            "metadata": json.loads(row[5]),
            "namespace": row[6],
            "file_hash": row[7]
        }

# Global accessor
_registry = None
def get_file_registry():
    global _registry
    if not _registry:
        _registry = FileRegistry()
    return _registry
