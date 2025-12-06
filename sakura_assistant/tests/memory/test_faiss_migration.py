import unittest
import sys
import os
from sakura_assistant.memory.faiss_store import get_memory_store, add_message_to_memory

class TestFaissMigration(unittest.TestCase):
    def test_store_initialization(self):
        store = get_memory_store()
        self.assertIsNotNone(store)
        self.assertIn("system_health", store.memory_stats)
        
    def test_add_message(self):
        store = get_memory_store()
        initial_count = len(store.conversation_history)
        add_message_to_memory("Test message", "user")
        self.assertEqual(len(store.conversation_history), initial_count + 1)
        
    def test_old_import_redirect(self):
        # Verify that importing from utils.storage (if somehow still referenced) 
        # would fail or we've cleaned it up.
        # Here we just check the new path works.
        try:
            from sakura_assistant.memory.faiss_store import get_memory_store
        except ImportError:
            self.fail("Could not import from new location")
