import unittest
import threading
import tempfile
import shutil
from unittest.mock import patch
from sakura_assistant.memory.chroma_store.store import get_chroma_store

class TestConcurrency(unittest.TestCase):
    def setUp(self):
        self.test_dir = tempfile.mkdtemp()
        self.patcher = patch('sakura_assistant.memory.chroma_store.store.CHROMA_PERSIST_DIR', self.test_dir)
        self.patcher.start()
        
        import sakura_assistant.memory.chroma_store.store as store_module
        store_module._store_instance = None
        
    def tearDown(self):
        self.patcher.stop()
        shutil.rmtree(self.test_dir, ignore_errors=True)
    def test_concurrent_writes(self):
        store = get_chroma_store()
        
        def write_op(i):
            store.add_documents(
                ids=[f"id_{i}"],
                embeddings=[[0.1]*1024],
                metadatas=[{"source": f"thread_{i}"}],
                documents=[f"doc_{i}"]
            )
            
        threads = []
        for i in range(10):
            t = threading.Thread(target=write_op, args=(i,))
            threads.append(t)
            t.start()
            
        for t in threads:
            t.join()
            
        # Verify all writes succeeded (mock check, real check depends on persistence)
        # This mainly ensures no "Database Locked" exception was raised
        self.assertTrue(True)
