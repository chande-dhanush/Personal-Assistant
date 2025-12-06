from sentence_transformers import SentenceTransformer

# Configuration
EMBEDDING_MODEL_NAME = "BAAI/bge-large-en-v1.5"

# Lazy load model
_embedding_model = None

def get_embedding_model():
    global _embedding_model
    if _embedding_model is None:
        print(f"🧠 Loading embedding model: {EMBEDDING_MODEL_NAME}...")
        try:
            _embedding_model = SentenceTransformer(EMBEDDING_MODEL_NAME)
        except Exception as e:
            print(f"❌ Failed to load embedding model: {e}")
            return None
    return _embedding_model
