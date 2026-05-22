"""Pydantic schemas for document and chunk serialization."""

import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class DocumentResponse(BaseModel):
    id: uuid.UUID
    filename: str
    file_type: str
    file_size: int
    status: str
    page_count: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class DocumentListResponse(BaseModel):
    documents: list[DocumentResponse]
    total: int


class ChunkResponse(BaseModel):
    id: uuid.UUID
    document_id: uuid.UUID
    content: str
    chunk_index: int
    token_count: int
    has_embedding: bool
    created_at: datetime

    class Config:
        from_attributes = True


class ChunkListResponse(BaseModel):
    chunks: list[ChunkResponse]
    total: int
