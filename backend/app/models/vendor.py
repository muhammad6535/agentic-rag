import uuid
from datetime import datetime
from sqlalchemy import Column, String, Text, DateTime, ForeignKey, JSON
from sqlalchemy.dialects.postgresql import UUID
from app.database import Base


class VendorAssessment(Base):
    __tablename__ = "vendor_assessments"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    document_id = Column(
        UUID(as_uuid=True),
        ForeignKey("documents.id", ondelete="SET NULL"),
        nullable=True,
    )
    original_filename = Column(String(255), nullable=False)
    company_name = Column(String(255), nullable=True)
    risk_type = Column(String(100), nullable=True)
    risk_level = Column(String(20), nullable=True)
    country = Column(String(100), nullable=True)
    business_unit = Column(String(255), nullable=True)
    compliance_notes = Column(Text, nullable=True)
    missing_fields = Column(JSON, default=list)
    extracted_raw = Column(JSON, default=dict)
    next_steps = Column(JSON, default=list)
    follow_up_email = Column(Text, nullable=True)
    status = Column(String(20), nullable=False, default="pending_review")
    human_notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
    updated_at = Column(DateTime(timezone=True), default=datetime.utcnow, onupdate=datetime.utcnow)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(
        UUID(as_uuid=True),
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    assessment_id = Column(
        UUID(as_uuid=True),
        ForeignKey("vendor_assessments.id", ondelete="CASCADE"),
        nullable=True,
    )
    action = Column(String(50), nullable=False)
    details = Column(JSON, default=dict)
    created_at = Column(DateTime(timezone=True), default=datetime.utcnow)
