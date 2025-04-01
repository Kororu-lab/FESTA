from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime

class Document(BaseModel):
    id: Optional[str] = None
    original_filename: str
    saved_filename: str
    file_path: str
    file_type: str
    upload_date: str
    file_size: int
    processed_file: Optional[str] = None
    text_length: Optional[int] = None
    processed_date: Optional[str] = None
    title: Optional[str] = None
    authors: Optional[List[str]] = None
    abstract: Optional[str] = None
    keywords: Optional[List[str]] = None
    publication_date: Optional[str] = None
    journal: Optional[str] = None
    doi: Optional[str] = None
    citations: Optional[List[str]] = None
    references: Optional[List[str]] = None
    categories: Optional[List[str]] = None
    tags: Optional[List[str]] = None
    vector_id: Optional[str] = None
    created_at: datetime = datetime.now()
    updated_at: datetime = datetime.now()

    class Config:
        from_attributes = True 