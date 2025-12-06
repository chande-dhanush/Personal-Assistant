# ChromaDB Integration Guide

## Overview
Sakura Assistant now uses a **Hybrid Memory Architecture**:
1.  **FAISS (Chat Memory):** Stores conversational history. Optimized for speed and short-term recall.
    - **Path:** `data/faiss_index.bin`
    - **Model:** `all-MiniLM-L6-v2`
2.  **ChromaDB (Document Memory):** Stores uploaded documents (PDFs, text files). Optimized for semantic search over long content.
    - **Path:** `data/chroma_store/`
    - **Model:** `BAAI/bge-large-en-v1.5`

## Isolation
The two systems are completely isolated:
- Different directories.
- Different embedding models.
- Different code paths (`utils/storage.py` vs `memory/chroma_store/`).

## API Usage

### 1. Ingestion
To ingest a document into Chroma:
```python
from sakura_assistant.memory.router import ingest_document

result = ingest_document("path/to/file.pdf", metadata={"category": "research"})
print(result)
```

### 2. Retrieval
To retrieve context from documents:
```python
from sakura_assistant.memory.router import get_document_retriever

retriever = get_document_retriever()
results = retriever.query("What does the document say about X?")
```

### 3. Agent Tool
The agent has access to `fetch_document_context(query)` tool, which wraps the retrieval logic.

## Configuration
- `ENABLE_CHROMA` (in `config.py`): Toggle ChromaDB functionality.
- `CHROMA_PERSIST_DIR`: Location of the database.

## Troubleshooting
- **Missing Dependencies:** Ensure `chromadb` and `sentence-transformers` are installed.
- **Model Loading:** The first run will download `BAAI/bge-large-en-v1.5` (~1.5GB). Ensure stable internet.
