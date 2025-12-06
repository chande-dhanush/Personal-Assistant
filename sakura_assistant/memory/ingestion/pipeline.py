import os
import uuid
import logging
import threading
from typing import Dict, Any, Optional, List
from concurrent.futures import ThreadPoolExecutor

from .handlers import get_handler_for_file
from .chunking import chunk_text_semantics
from ..chroma_store.store import get_chroma_store
from ...utils.file_registry import get_file_registry
from ...core.ingest_state import set_ingesting

# Configure logging
logger = logging.getLogger(__name__)

class IngestionPipeline:
    """
    Robust ingestion pipeline with background processing and validation.
    """
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=2) # Limit concurrency
        self._lock = threading.Lock()

    def ingest_file_async(self, file_path: str, metadata: Optional[Dict] = None) -> str:
        """
        Submit a file for ingestion in the background.
        Returns a tracking ID or file ID immediately.
        """
        file_id = str(uuid.uuid4())
        self.executor.submit(self._process_file, file_path, file_id, metadata)
        return file_id

    def ingest_file_sync(self, file_path: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Blocking ingestion for immediate feedback (e.g. small files).
        """
        file_id = str(uuid.uuid4())
        return self._process_file(file_path, file_id, metadata)

    def _process_file(self, file_path: str, file_id: str, metadata: Optional[Dict] = None) -> Dict[str, Any]:
        set_ingesting(True)
        try:
            if not os.path.exists(file_path):
                return {"error": True, "message": "File not found."}

            filename = os.path.basename(file_path)
            
            # 1. Get Handler
            handler = get_handler_for_file(file_path)
            if not handler:
                return {"error": True, "message": f"No handler for file type: {filename}"}

            # 2. Extract Text
            text = handler.extract_text(file_path)
            if not text or not text.strip():
                return {"error": True, "message": "Extracted text is empty."}

            # 3. Chunking
            chunks = chunk_text_semantics(text, metadata={"source": filename, "filename": filename, "file_id": file_id})
            
            if not chunks:
                return {"error": True, "message": "No chunks generated."}

            # 4. Store in Chroma (Thread-safe)
            store = get_chroma_store()
            
            # 3.5 Generate Embeddings
            from ..chroma_store.model import get_embedding_model
            model = get_embedding_model()
            
            ids = [c["id"] for c in chunks]
            texts = [c["text"] for c in chunks]
            metadatas = [c["metadata"] for c in chunks]
            
            embeddings = model.encode(texts).tolist()
            
            # Add file_id to all metadatas
            for m in metadatas:
                m["file_id"] = file_id
                if metadata:
                    m.update(metadata)

            store.add_documents(ids, embeddings, metadatas, texts)

            # 5. Register File
            registry = get_file_registry()
            registry.add_file(
                file_id=file_id,
                filename=filename,
                file_type=handler.file_type,
                chunk_count=len(chunks),
                metadata=metadatas[0] if metadatas else {}
            )

            return {
                "error": False,
                "file_id": file_id,
                "filename": filename,
                "chunks": len(chunks),
                "message": f"✅ Ingested {filename} ({len(chunks)} chunks)"
            }

        except Exception as e:
            logger.error(f"Ingestion failed for {file_path}: {e}")
            return {"error": True, "message": f"Ingestion failed: {str(e)}"}
        finally:
            set_ingesting(False)

# Singleton
_pipeline = IngestionPipeline()

def get_ingestion_pipeline():
    return _pipeline
