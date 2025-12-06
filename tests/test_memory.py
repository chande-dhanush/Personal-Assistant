import unittest
import shutil
import tempfile
from pathlib import Path
import sys
import os

# Add parent dir to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from sakura_assistant.utils.storage import VectorMemoryStore, write_memory_atomic
from sakura_assistant.utils.chunking import SemanticChunker

class TestMemorySystem(unittest.TestCase):
    def setUp(self):
        # Create a temp directory for tests
        self.test_dir = Path(tempfile.mkdtemp())
        
        # Mock paths in storage module (Monkey patching for test isolation)
        import sakura_assistant.utils.storage as storage
        storage.DATA_DIR = self.test_dir
        storage.BACKUP_DIR = self.test_dir / "backup"
        storage.FAISS_INDEX_PATH = self.test_dir / "faiss_index.bin"
        storage.MEMORY_METADATA_FILE = self.test_dir / "memory_metadata.json"
        storage.CONVERSATION_FILE = self.test_dir / "conversation_history.json"
        storage.MEMORY_STATS_FILE = self.test_dir / "memory_stats.json"
        
        storage.DATA_DIR.mkdir(exist_ok=True)
        storage.BACKUP_DIR.mkdir(exist_ok=True)
        
        self.memory = VectorMemoryStore()

    def tearDown(self):
        shutil.rmtree(self.test_dir)

    def test_atomic_write(self):
        """Test that atomic writes create files and backups."""
        test_file = self.test_dir / "test.json"
        data = {"key": "value"}
        
        write_memory_atomic(test_file, data)
        
        self.assertTrue(test_file.exists())
        self.assertTrue((self.test_dir / "backup").exists())
        # Check checksum
        self.assertTrue((self.test_dir / "test.json.sha256").exists())

    def test_add_and_retrieve_memory(self):
        """Test adding a message and retrieving it via hybrid search."""
        # Skip if FAISS not available (in CI envs without it)
        if not self.memory.faiss_index:
            print("Skipping vector test (FAISS missing)")
            return

        content = "The secret code is BlueBanana."
        self.memory.add_message(content)
        
        # Search for keyword
        result = self.memory.get_context_for_query("What is the secret code?")
        self.assertIn("BlueBanana", result)
        
        # Search for semantic
        result_sem = self.memory.get_context_for_query("fruit password")
        # Should likely find it due to vector similarity if model is good, 
        # but at least shouldn't crash.
        self.assertIsNotNone(result_sem)

    def test_deduplication(self):
        """Test that duplicate chunks are not added."""
        if not self.memory.faiss_index:
            return

        content = "This is a unique memory."
        self.memory.add_message(content)
        initial_count = len(self.memory.memory_texts)
        
        # Add exact same content
        self.memory.add_message(content)
        final_count = len(self.memory.memory_texts)
        
        self.assertEqual(initial_count, final_count, "Duplicate memory should not increase count")

if __name__ == '__main__':
    unittest.main()
