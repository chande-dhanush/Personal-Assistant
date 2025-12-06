from pydantic import BaseModel, Field
from typing import Optional, List, Dict, Any
from datetime import datetime

class DocumentMetadata(BaseModel):
    source: str # "document" or "user_upload"
    filename: str
    file_id: str
    chunk_index: int
    page_number: Optional[int] = None
    ingested_at: str = Field(default_factory=lambda: datetime.now().isoformat())
    custom_metadata: Dict[str, Any] = {}

class Chunk(BaseModel):
    text: str
    metadata: DocumentMetadata
    embedding: Optional[List[float]] = None
