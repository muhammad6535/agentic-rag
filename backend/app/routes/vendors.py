import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.vendor import VendorAssessment, AuditLog
from app.models.document import Document
from app.models.user import User
from app.schemas.vendor import (
    VendorUploadResponse,
    VendorListResponse,
    VendorDetailResponse,
    VendorApproveRequest,
    VendorDashboardResponse,
    AuditEntryResponse,
)
from app.services.document_loader import DocumentLoader
from app.services.vendor_service import VendorRiskService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/vendors", tags=["vendors"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


async def _log_audit(db, user_id, assessment_id, action, details=None):
    entry = AuditLog(
        id=uuid.uuid4(),
        user_id=user_id,
        assessment_id=assessment_id,
        action=action,
        details=details or {},
        created_at=datetime.utcnow(),
    )
    db.add(entry)


def _assessment_to_response(a: VendorAssessment) -> VendorUploadResponse:
    return VendorUploadResponse(
        id=a.id,
        original_filename=a.original_filename,
        company_name=a.company_name,
        risk_type=a.risk_type,
        risk_level=a.risk_level,
        country=a.country,
        business_unit=a.business_unit,
        compliance_notes=a.compliance_notes,
        missing_fields=a.missing_fields or [],
        next_steps=a.next_steps or [],
        follow_up_email=a.follow_up_email,
        status=a.status,
        created_at=a.created_at,
    )


@router.post("/upload", response_model=VendorUploadResponse, status_code=201)
async def upload_vendor_document(
    file: UploadFile = File(...),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename)[1].lower()
    if ext not in DocumentLoader.SUPPORTED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported file type '{ext}'. Supported: {DocumentLoader.SUPPORTED_EXTENSIONS}",
        )

    # Save file
    file_id = uuid.uuid4()
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    content_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(content_bytes)

    # Extract text
    try:
        text_content, _ = DocumentLoader.extract_text(file_path)
    except ValueError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    # Save as document record
    document = Document(
        id=file_id,
        user_id=current_user.id,
        filename=file.filename,
        file_type=ext.lstrip("."),
        file_size=len(content_bytes),
        status="ready",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(document)
    await db.flush()

    # Run AI assessment
    service = VendorRiskService()
    try:
        result = await service.run_full_assessment(text_content, file.filename)
    except Exception as e:
        result = {
            "company_name": None,
            "risk_type": None,
            "risk_level": "Medium",
            "country": None,
            "business_unit": None,
            "compliance_notes": None,
            "missing_fields": [],
            "extracted_raw": {},
            "next_steps": [],
            "follow_up_email": None,
            "classification_reasoning": "",
        }

    # Create assessment
    assessment = VendorAssessment(
        id=uuid.uuid4(),
        user_id=current_user.id,
        document_id=document.id,
        original_filename=file.filename,
        company_name=result.get("company_name"),
        risk_type=result.get("risk_type"),
        risk_level=result.get("risk_level", "Medium"),
        country=result.get("country"),
        business_unit=result.get("business_unit"),
        compliance_notes=result.get("compliance_notes"),
        missing_fields=result.get("missing_fields", []),
        extracted_raw=result.get("extracted_raw", {}),
        next_steps=result.get("next_steps", []),
        follow_up_email=result.get("follow_up_email"),
        status="pending_review",
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(assessment)
    await db.flush()

    await _log_audit(db, current_user.id, assessment.id, "document_uploaded", {
        "filename": file.filename, "risk_level": assessment.risk_level
    })
    await _log_audit(db, current_user.id, assessment.id, "ai_extraction_complete", {
        "company_name": assessment.company_name,
        "risk_level": assessment.risk_level,
    })

    await db.commit()
    await db.refresh(assessment)
    return _assessment_to_response(assessment)


@router.get("", response_model=VendorListResponse)
async def list_assessments(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    status: str = Query(None, description="Filter by status"),
    risk_level: str = Query(None, description="Filter by risk level"),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=100),
):
    stmt = select(VendorAssessment).where(VendorAssessment.user_id == current_user.id)
    if status:
        stmt = stmt.where(VendorAssessment.status == status)
    if risk_level:
        stmt = stmt.where(VendorAssessment.risk_level == risk_level)
    stmt = stmt.order_by(desc(VendorAssessment.created_at)).offset(skip).limit(limit)

    result = await db.execute(stmt)
    assessments = result.scalars().all()

    count_stmt = select(func.count(VendorAssessment.id)).where(
        VendorAssessment.user_id == current_user.id
    )
    if status:
        count_stmt = count_stmt.where(VendorAssessment.status == status)
    total = (await db.execute(count_stmt)).scalar()

    return VendorListResponse(
        assessments=[_assessment_to_response(a) for a in assessments],
        total=total or 0,
    )


@router.get("/dashboard", response_model=VendorDashboardResponse)
async def get_dashboard(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    base = select(VendorAssessment).where(VendorAssessment.user_id == current_user.id)

    total = (await db.execute(
        select(func.count(VendorAssessment.id)).where(VendorAssessment.user_id == current_user.id)
    )).scalar() or 0

    async def _count(field: str, value: str) -> int:
        stmt = select(func.count(VendorAssessment.id)).where(
            VendorAssessment.user_id == current_user.id,
            getattr(VendorAssessment, field) == value,
        )
        return (await db.execute(stmt)).scalar() or 0

    recent = (await db.execute(
        base.order_by(desc(VendorAssessment.created_at)).limit(5)
    )).scalars().all()

    return VendorDashboardResponse(
        total_assessments=total,
        critical_count=await _count("risk_level", "Critical"),
        high_count=await _count("risk_level", "High"),
        medium_count=await _count("risk_level", "Medium"),
        low_count=await _count("risk_level", "Low"),
        pending_review=await _count("status", "pending_review"),
        approved_count=await _count("status", "approved"),
        recent_assessments=[_assessment_to_response(a) for a in recent],
    )


@router.get("/{assessment_id}", response_model=VendorDetailResponse)
async def get_assessment(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(VendorAssessment).where(
        VendorAssessment.id == assessment_id,
        VendorAssessment.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")

    audit_stmt = (
        select(AuditLog)
        .where(AuditLog.assessment_id == a.id)
        .order_by(AuditLog.created_at.asc())
    )
    audit_result = await db.execute(audit_stmt)
    audit_entries = audit_result.scalars().all()

    return VendorDetailResponse(
        id=a.id,
        original_filename=a.original_filename,
        company_name=a.company_name,
        risk_type=a.risk_type,
        risk_level=a.risk_level,
        country=a.country,
        business_unit=a.business_unit,
        compliance_notes=a.compliance_notes,
        missing_fields=a.missing_fields or [],
        extracted_raw=a.extracted_raw or {},
        next_steps=a.next_steps or [],
        follow_up_email=a.follow_up_email,
        status=a.status,
        human_notes=a.human_notes,
        created_at=a.created_at,
        updated_at=a.updated_at,
        audit_log=[
            AuditEntryResponse(
                id=e.id,
                action=e.action,
                details=e.details or {},
                created_at=e.created_at,
            )
            for e in audit_entries
        ],
    )


@router.post("/{assessment_id}/approve", response_model=VendorUploadResponse)
async def approve_assessment(
    assessment_id: uuid.UUID,
    request: VendorApproveRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(VendorAssessment).where(
        VendorAssessment.id == assessment_id,
        VendorAssessment.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    a = result.scalar_one_or_none()
    if not a:
        raise HTTPException(status_code=404, detail="Assessment not found")

    action = "approved" if request.approved else "rejected"
    a.status = action
    a.human_notes = request.notes
    a.updated_at = datetime.utcnow()

    await _log_audit(db, current_user.id, a.id, f"human_{action}", {
        "notes": request.notes,
    })
    await db.commit()
    await db.refresh(a)
    return _assessment_to_response(a)


@router.get("/{assessment_id}/audit", response_model=list[AuditEntryResponse])
async def get_audit_log(
    assessment_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(VendorAssessment).where(
        VendorAssessment.id == assessment_id,
        VendorAssessment.user_id == current_user.id,
    )
    if not (await db.execute(stmt)).scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Assessment not found")

    audit_stmt = (
        select(AuditLog)
        .where(AuditLog.assessment_id == assessment_id)
        .order_by(AuditLog.created_at.asc())
    )
    result = await db.execute(audit_stmt)
    entries = result.scalars().all()

    return [
        AuditEntryResponse(id=e.id, action=e.action, details=e.details or {}, created_at=e.created_at)
        for e in entries
    ]
