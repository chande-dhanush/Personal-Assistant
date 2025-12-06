import unittest
import os
import shutil
from sakura_assistant.memory.ingestion.pipeline import get_ingestion_pipeline
from sakura_assistant.memory.ingestion.handlers import get_handler_for_file

class TestIngestionPipeline(unittest.TestCase):
    def setUp(self):
        self.test_file = "test_ingest.txt"
        with open(self.test_file, "w") as f:
            f.write("This is a test document for the new ingestion pipeline. " * 20)
            
    def tearDown(self):
        if os.path.exists(self.test_file):
            os.remove(self.test_file)

    def test_handler_selection(self):
        handler = get_handler_for_file("test.pdf")
        self.assertEqual(handler.file_type, "pdf")
        
        handler = get_handler_for_file("test.txt")
        self.assertEqual(handler.file_type, "text")

    def test_sync_ingestion(self):
        pipeline = get_ingestion_pipeline()
        result = pipeline.ingest_file_sync(self.test_file)
        
        self.assertFalse(result["error"])
        self.assertIn("Ingested", result["message"])
        self.assertTrue(result["chunks"] > 0)
