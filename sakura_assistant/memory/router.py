from typing import Any, Optional
from ..config import is_feature_enabled
from .faiss_store import get_memory_store

# Lazy load Chroma to avoid overhead if disabled
_chroma_retriever = None

def get_chat_retriever():
    """
    Returns the FAISS retriever for conversational memory.
    Strictly for chat history.
    """
    # Re-use existing FAISS store from memory.faiss_store
    return get_memory_store()

def get_document_retriever():
    """
    Returns the Chroma retriever for document memory.
    Strictly for long-form documents (PDFs, uploads).
    """
    global _chroma_retriever
    
    if not is_feature_enabled("enable_chroma"):
        print("⚠️ ChromaDB is disabled in config.")
        return None
        
    if _chroma_retriever is None:
        try:
            from .chroma_store.retriever import ChromaDocumentRetriever
            _chroma_retriever = ChromaDocumentRetriever()
        except ImportError as e:
            print(f"❌ Failed to import ChromaDocumentRetriever: {e}")
            return None
            
    return _chroma_retriever

def ingest_document(file_path: str, metadata: Optional[dict] = None):
    """
    Ingests a document into ChromaDB.
    """
    if not is_feature_enabled("enable_chroma"):
        return {"error": True, "message": "ChromaDB is disabled."}
        
    try:
        from .ingestion.pipeline import get_ingestion_pipeline
        pipeline = get_ingestion_pipeline()
        return pipeline.ingest_file_sync(file_path, metadata)
    except Exception as e:
        return {"error": True, "message": f"Ingestion failed: {e}"}
