import os
import json
import fitz  # PyMuPDF
import docx
from abc import ABC, abstractmethod
from typing import Optional

class FileHandler(ABC):
    @abstractmethod
    def extract_text(self, path: str) -> str:
        pass
    
    @property
    @abstractmethod
    def file_type(self) -> str:
        pass

class PDFHandler(FileHandler):
    def extract_text(self, path: str) -> str:
        doc = fitz.open(path)
        text = ""
        for page in doc:
            text += page.get_text()
        return text
    
    @property
    def file_type(self) -> str:
        return "pdf"

class DocxHandler(FileHandler):
    def extract_text(self, path: str) -> str:
        doc = docx.Document(path)
        return "\n".join([p.text for p in doc.paragraphs])

    @property
    def file_type(self) -> str:
        return "docx"

class TextHandler(FileHandler):
    def extract_text(self, path: str) -> str:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            return f.read()

    @property
    def file_type(self) -> str:
        return "text"

def get_handler_for_file(path: str) -> Optional[FileHandler]:
    ext = os.path.splitext(path)[1].lower()
    if ext == ".pdf":
        return PDFHandler()
    elif ext == ".docx":
        return DocxHandler()
    elif ext in [".txt", ".md", ".py", ".js", ".json", ".csv"]:
        return TextHandler()
    return None
