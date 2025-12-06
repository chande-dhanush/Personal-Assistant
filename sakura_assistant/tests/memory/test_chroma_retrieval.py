import unittest
import os
import shutil
import tempfile
from unittest.mock import patch
from sakura_assistant.memory.ingestion.pipeline import get_ingestion_pipeline
from sakura_assistant.memory.chroma_store.retriever import ChromaDocumentRetriever
from sakura_assistant.memory.chroma_store.store import get_chroma_store

class TestChromaRetrieval(unittest.TestCase):
    def setUp(self):
        # Create temp dir for Chroma
        self.test_dir = tempfile.mkdtemp()
        # Patch the variable in store.py, NOT config.py
        self.patcher = patch('sakura_assistant.memory.chroma_store.store.CHROMA_PERSIST_DIR', self.test_dir)
        self.patcher.start()
        
        # Force re-init of store with new path
        import sakura_assistant.memory.chroma_store.store as store_module
        store_module._store_instance = None
        
        self.test_file = "test_retrieval.txt"
        with open(self.test_file, "w") as f:
            f.write("The secret code is BLUEBERRY_PIE. " * 10)
        
        # Ingest
        pipeline = get_ingestion_pipeline()
        pipeline.ingest_file_sync(self.test_file)
        
    def tearDown(self):
        self.patcher.stop()
        if os.path.exists(self.test_file):
            os.remove(self.test_file)
        shutil.rmtree(self.test_dir, ignore_errors=True)

    def test_retrieval(self):
        retriever = ChromaDocumentRetriever()
        results = retriever.query("What is the secret code?")
        
        self.assertTrue(len(results) > 0)
        # Check rich return format
        first = results[0]
        self.assertIn("content", first)
        self.assertIn("metadata", first)
        self.assertIn("score", first)
        self.assertIn("BLUEBERRY_PIE", first["content"])

        self.assertEqual(first["metadata"]["filename"], "test_retrieval.txt")
