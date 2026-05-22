import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class SourceChunk(BaseModel):
    id: str
    content: str
    document_name: str
    chunk_index: int
    score: float


class AskRequest(BaseModel):
    question: str
    session_id: Optional[str] = None
    document_id: Optional[str] = None


class AskResponse(BaseModel):
    answer: str
    session_id: str
    sources: list[SourceChunk]


class ChatMessageResponse(BaseModel):
    id: uuid.UUID
    session_id: uuid.UUID
    role: str
    content: str
    document_id: Optional[uuid.UUID] = None
    sources: Optional[list] = None
    created_at: datetime

    class Config:
        from_attributes = True


class ChatHistoryResponse(BaseModel):
    messages: list[ChatMessageResponse]
    total: int


class SessionSummary(BaseModel):
    session_id: str
    last_message_at: datetime
    preview: str


class SessionListResponse(BaseModel):
    sessions: list[SessionSummary]
    total: int
