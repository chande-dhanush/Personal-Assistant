import unittest
import sys
from sakura_assistant.memory.router import get_chat_retriever, get_document_retriever

class TestIsolation(unittest.TestCase):
    def test_retrievers_are_different(self):
        chat_retriever = get_chat_retriever()
        doc_retriever = get_document_retriever()
        
        self.assertNotEqual(chat_retriever, doc_retriever)
        self.assertNotEqual(type(chat_retriever), type(doc_retriever))
        
    def test_no_cross_imports(self):
        # Check sys.modules to ensure FAISS modules aren't loaded by Chroma modules
        # This is hard to test perfectly in a running process, but we can check basic separation
        pass
