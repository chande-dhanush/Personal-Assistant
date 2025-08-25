import os
import json
import numpy as np
import faiss
from datetime import datetime
from sentence_transformers import SentenceTransformer
from typing import List, Dict
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from ..config import CONV_HISTORY_FILE, CONTACTS_FILE
import dotenv

# Load environment variables
dotenv.load_dotenv()
# Ensure the environment variables are loaded
if not os.getenv("GOOGLE_API_KEY"):
    raise ValueError("GOOGLE_API_KEY must be set in the environment variables.")

# === CONFIGURATION ===
MEMORY_MODEL_NAME = "all-MiniLM-L6-v2"
MEMORY_DIM = 384
EMBEDDING_MODEL = SentenceTransformer(MEMORY_MODEL_NAME)

# === Gemini Summarization Setup ===
GEMINI_LLM = ChatGoogleGenerativeAI(model="gemini-2.0-flash", google_api_key=os.getenv("GOOGLE_API_KEY"))
GEMINI_SUMMARY_PROMPT = ChatPromptTemplate.from_template("""
You're an agent helping summarize a long conversation history. Focus on relevant facts, entities, and actions.
Summarize the following conversation into 4–6 bullet points:

{log}
""")



# === 🧠 Vector Memory Class ===
class MemoryVectorStore:
    def __init__(self):
        self.index = faiss.IndexFlatL2(MEMORY_DIM)
        self.text_chunks = []
        self.timestamps = []

    def normalize(self, text: str) -> str:
        return text.strip().lower()

    def add_chunk(self, text: str):
        if not text:
            return
        text = self.normalize(text)
        vector = EMBEDDING_MODEL.encode([text], normalize_embeddings=True)
        self.index.add(np.array(vector).astype("float32"))
        self.text_chunks.append(text)
        self.timestamps.append(datetime.utcnow())

    def search(self, query: str, top_k=5) -> List[str]:
        if not self.text_chunks:
            return []
        vector = EMBEDDING_MODEL.encode([self.normalize(query)], normalize_embeddings=True)
        D, I = self.index.search(np.array(vector).astype("float32"), top_k)
        return [self.text_chunks[i] for i in I[0] if i < len(self.text_chunks) and D[0][i] < 1.0]

    def rebuild_from_history(self, conversation: List[Dict]):
        self.index.reset()
        self.text_chunks.clear()
        self.timestamps.clear()
        for entry in conversation:
            text = entry.get("content")
            if text:
                self.add_chunk(text)

    def clear(self):
        self.index.reset()
        self.text_chunks.clear()
        self.timestamps.clear()

# === 🔄 Memory History Engine ===
memory_store = MemoryVectorStore()

def save_conversation(history: List[Dict]):
    """Saves entire history and refreshes vector store."""
    try:
        # Optional: Compress old messages into a summarized block before saving
        if len(history) > 20:
            summary = summarize_memory_with_gemini(history[:-8])  # Keep last 8 messages as-is
            if summary:
                history = [{"role": "assistant", "content": summary}] + history[-8:]

        with open(CONV_HISTORY_FILE, 'w', encoding='utf-8') as f:
            json.dump(history, f, ensure_ascii=False, indent=2)

        memory_store.rebuild_from_history(history)
    except Exception as e:
        print(f"💾 Error saving conversation: {str(e)}")

def load_conversation() -> List[Dict]:
    """Loads and returns previous conversation from disk (and restores memory)."""
    history = []
    try:
        if os.path.exists(CONV_HISTORY_FILE):
            with open(CONV_HISTORY_FILE, 'r', encoding='utf-8') as f:
                history = json.load(f)
                memory_store.rebuild_from_history(history)
    except Exception as e:
        print(f"📂 Error loading conversation: {str(e)}")
    return history

def clear_conversation_history() -> bool:
    try:
        open(CONV_HISTORY_FILE, 'w').write('[]')
        memory_store.clear()
        return True
    except Exception as e:
        print(f"🧹 Error clearing history: {str(e)}")
        return False

# === NEW: Gemini summarizer leveraged right here ===
def summarize_memory_with_gemini(convo: List[Dict]) -> str:
    """Summarize a long conversation using Gemini 1.5 Pro."""
    try:
        if not convo:
            return ""

        # Convert to readable text
        text_chunks = []
        for msg in convo:
            role = msg.get("role", "User").capitalize()
            content = msg.get("content", "")
            if content:
                text_chunks.append(f"{role}: {content}")
        log_text = "\n".join(text_chunks)

        final_prompt = GEMINI_SUMMARY_PROMPT.format(log=log_text)
        output = GEMINI_LLM.invoke(final_prompt)
        return str(output) if output else ""
    except Exception as e:
        print(f"📝 Gemini summarization failed: {e}")
        return ""

# === 📖 Contact Book ===
def load_contacts() -> Dict[str, str]:
    try:
        if os.path.exists(CONTACTS_FILE):
            with open(CONTACTS_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
    except json.JSONDecodeError:
        print("⚠️ Corrupt contacts file, will ignore.")
    except Exception as e:
        print(f"Error loading contacts: {str(e)}")
    return {}

def save_contacts(contacts: Dict[str, str]):
    try:
        with open(CONTACTS_FILE, 'w', encoding='utf-8') as f:
            json.dump(contacts, f, indent=2)
    except Exception as e:
        print(f"Error saving contacts: {str(e)}")

def add_contact(name: str, number: str) -> bool:
    try:
        name = name.strip().lower()
        number = number.strip()
        if not name or not number:
            return False
        contacts = load_contacts()
        contacts[name] = number
        save_contacts(contacts)
        return True
    except Exception as e:
        print(f"Error adding contact: {str(e)}")
        return False