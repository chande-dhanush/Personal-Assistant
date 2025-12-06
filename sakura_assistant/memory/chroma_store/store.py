import os
import chromadb
from chromadb.config import Settings
from ...config import get_config, CHROMA_PERSIST_DIR
import threading

class ChromaStore:
    _instance = None
    _lock = threading.Lock()
    
    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super(ChromaStore, cls).__new__(cls)
                    cls._instance._initialized = False
        return cls._instance
        
    def __init__(self):
        if self._initialized:
            return
            
        print(f"🔌 Initializing ChromaDB at {CHROMA_PERSIST_DIR}...")
        os.makedirs(CHROMA_PERSIST_DIR, exist_ok=True)
        
        try:
            self.client = chromadb.PersistentClient(path=CHROMA_PERSIST_DIR)
            self.collection = self.client.get_or_create_collection(
                name="sakura_documents",
                metadata={"hnsw:space": "cosine"}
            )
            self.write_lock = threading.Lock()
            print("✅ ChromaDB initialized successfully.")
            self._initialized = True
        except Exception as e:
            print(f"❌ Failed to initialize ChromaDB: {e}")
            self.client = None
            self.collection = None
            self.write_lock = threading.Lock()

    def add_documents(self, ids, embeddings, metadatas, documents):
        if not self.collection:
            return False
        try:
            with self.write_lock:
                self.collection.add(
                    ids=ids,
                    embeddings=embeddings,
                    metadatas=metadatas,
                    documents=documents
                )
            return True
        except Exception as e:
            print(f"⚠️ Chroma add failed: {e}")
            return False

    def query(self, query_embeddings, n_results=5, where=None):
        if not self.collection:
            return None
        try:
            return self.collection.query(
                query_embeddings=query_embeddings,
                n_results=n_results,
                where=where
            )
        except Exception as e:
            print(f"⚠️ Chroma query failed: {e}")
            return None
            
    def delete(self, where):
        if not self.collection:
            return False
        try:
            with self.write_lock:
                self.collection.delete(where=where)
            return True
        except Exception as e:
            print(f"⚠️ Chroma delete failed: {e}")
            return False

def get_chroma_store():
    return ChromaStore()
