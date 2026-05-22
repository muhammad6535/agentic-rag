import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class VendorUploadResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    company_name: Optional[str] = None
    risk_type: Optional[str] = None
    risk_level: Optional[str] = None
    country: Optional[str] = None
    business_unit: Optional[str] = None
    compliance_notes: Optional[str] = None
    missing_fields: list[str]
    next_steps: list[str]
    follow_up_email: Optional[str] = None
    status: str
    created_at: datetime


class VendorListResponse(BaseModel):
    assessments: list[VendorUploadResponse]
    total: int


class VendorDetailResponse(BaseModel):
    id: uuid.UUID
    original_filename: str
    company_name: Optional[str] = None
    risk_type: Optional[str] = None
    risk_level: Optional[str] = None
    country: Optional[str] = None
    business_unit: Optional[str] = None
    compliance_notes: Optional[str] = None
    missing_fields: list[str]
    extracted_raw: dict
    next_steps: list[str]
    follow_up_email: Optional[str] = None
    status: str
    human_notes: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    audit_log: list["AuditEntryResponse"]


class AuditEntryResponse(BaseModel):
    id: uuid.UUID
    action: str
    details: dict
    created_at: datetime


class VendorApproveRequest(BaseModel):
    approved: bool
    notes: Optional[str] = None


class VendorDashboardResponse(BaseModel):
    total_assessments: int
    critical_count: int
    high_count: int
    medium_count: int
    low_count: int
    pending_review: int
    approved_count: int
    recent_assessments: list[VendorUploadResponse]
