import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, Float, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    question = Column(Text, nullable=False)
    answer = Column(Text, nullable=False)
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    document_name = Column(String(255), nullable=True)
    faithfulness_score = Column(Float, default=0.0)
    answer_relevance_score = Column(Float, default=0.0)
    context_relevance_score = Column(Float, default=0.0)
    hallucination_score = Column(Float, default=0.0)
    overall_score = Column(Float, default=0.0)
    supported_claims = Column(JSON, default=list)
    unsupported_claims = Column(JSON, default=list)
    sources_used = Column(JSON, default=list)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
