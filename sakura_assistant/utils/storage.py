import json
import os
import numpy as np
import faiss
from sentence_transformers import SentenceTransformer
from ..config import CONV_HISTORY_FILE, CONTACTS_FILE

# === Embedding Model & Vector Store ===
EMBEDDING_MODEL = SentenceTransformer("all-MiniLM-L6-v2", device='cpu')
MEMORY_DIM = 384
os.environ['TRANSFORMERS_NO_TF'] = '1'
os.environ['TF_ENABLE_ONEDNN_OPTS'] = '0'  # Disable oneDNN optimizations for compatibility

class MemoryVectorStore:
    def __init__(self):
        self.index = faiss.IndexFlatL2(MEMORY_DIM)
        self.text_chunks = []

    def add_chunk(self, text):
        embedding = EMBEDDING_MODEL.encode([text])
        self.index.add(np.array(embedding).astype("float32"))
        self.text_chunks.append(text)

    def search(self, query, top_k=5):
        if not self.text_chunks:
            return []
        embedding = EMBEDDING_MODEL.encode([query])
        D, I = self.index.search(np.array(embedding).astype("float32"), top_k)
        return [self.text_chunks[i] for i in I[0] if i < len(self.text_chunks)]

    def rebuild_from_history(self, history):
        self.index.reset()
        self.text_chunks.clear()
        for entry in history:
            content = entry.get("content")
            if content:
                self.add_chunk(content)

# Global memory store
memory_store = MemoryVectorStore()

def clear_conversation_history():
    try:
        with open(CONV_HISTORY_FILE, 'w') as f:
            json.dump([], f)
        memory_store.index.reset()
        memory_store.text_chunks.clear()
        print("Conversation history cleared successfully.")
        return True
    except Exception as e:
        print(f"Error clearing conversation history: {str(e)}")
        return False

def load_conversation():
    try:
        if os.path.exists(CONV_HISTORY_FILE):
            with open(CONV_HISTORY_FILE, 'r') as f:
                history = json.load(f)
                memory_store.rebuild_from_history(history)
                return history
    except Exception as e:
        print(f"Error loading conversation: {str(e)}")
    return []

def save_conversation(history):
    try:
        with open(CONV_HISTORY_FILE, 'w') as f:
            json.dump(history, f)
        memory_store.rebuild_from_history(history)
    except Exception as e:
        print(f"Error saving conversation: {str(e)}")

# === Contact Book Functions ===
def load_contacts():
    print("Loading contacts from file...")
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, 'r') as f:
                print("Contacts file found, loading...")
                return json.load(f)
    except Exception as e:
        print(f"Error loading contacts: {str(e)}")
    return {}  # Default contacts

def save_contacts(contacts):
    try:
        with open(CONTACTS_FILE, 'w') as f:
            json.dump(contacts, f)
    except Exception as e:
        print(f"Error saving contacts: {str(e)}")

def add_contact(name, number):
    if not name or not number:
        return False
    try:
        contacts = load_contacts()
        contacts[name.lower()] = number
        save_contacts(contacts)
        return True
    except Exception as e:
        print(f"Error adding contact: {str(e)}")
        return False
