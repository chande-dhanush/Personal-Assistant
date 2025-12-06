from typing import List, Dict, Any
from .store import get_chroma_store
from .model import get_embedding_model

class ChromaDocumentRetriever:
    def __init__(self):
        self.store = get_chroma_store()
        self.model = get_embedding_model()

    def query(self, query_text: str, n_results: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.model.encode([query_text]).tolist()
        
        results = self.store.query(
            query_embeddings=query_embedding,
            n_results=n_results
            # Removed 'where' constraint to allow broader search if needed, 
            # or keep it if 'source' is strictly managed.
        )
        
        formatted_results = []
        if results and results['ids']:
            ids = results['ids'][0]
            docs = results['documents'][0]
            metas = results['metadatas'][0]
            distances = results['distances'][0] if 'distances' in results else [0.0]*len(ids)
            
            for id, doc, meta, dist in zip(ids, docs, metas, distances):
                formatted_results.append({
                    "id": id,
                    "content": doc,
                    "metadata": meta,
                    "score": 1.0 - dist, # Convert distance to similarity score approx
                    "distance": dist
                })
                
        return formatted_results
