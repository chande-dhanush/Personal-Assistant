# Global Ingestion State
# Used to prevent RAG queries while embeddings are being built.

_is_ingesting = False

def set_ingesting(flag: bool):
    global _is_ingesting
    _is_ingesting = flag

def get_ingesting() -> bool:
    return _is_ingesting