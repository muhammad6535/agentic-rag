import os
import uuid
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.config import settings
from app.models.document import Document, Chunk
from app.models.user import User
from app.schemas.document import (
    DocumentResponse,
    DocumentListResponse,
    ChunkResponse,
    ChunkListResponse,
)
from app.services.document_loader import DocumentLoader
from app.services.text_splitter import TextSplitterService
from app.services.embedding_service import EmbeddingService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/documents", tags=["documents"])

UPLOAD_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "uploads")
os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload", response_model=DocumentResponse, status_code=201)
async def upload_document(
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

    max_bytes = settings.max_upload_size_mb * 1024 * 1024
    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)
    if file_size > max_bytes:
        raise HTTPException(
            status_code=400,
            detail=f"File too large. Max size: {settings.max_upload_size_mb}MB",
        )

    file_id = uuid.uuid4()
    safe_filename = f"{file_id}{ext}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)
    content_bytes = await file.read()
    with open(file_path, "wb") as f:
        f.write(content_bytes)

    try:
        text_content, page_count = DocumentLoader.extract_text(file_path)
    except ValueError as e:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise HTTPException(status_code=400, detail=str(e))

    document = Document(
        id=file_id,
        user_id=current_user.id,
        filename=file.filename,
        file_type=ext.lstrip("."),
        file_size=file_size,
        status="processing",
        page_count=page_count or 0,
        created_at=datetime.utcnow(),
        updated_at=datetime.utcnow(),
    )
    db.add(document)
    await db.flush()

    try:
        splitter = TextSplitterService()
        chunk_data = splitter.split_with_metadata(text_content)

        embedding_service = EmbeddingService()
        texts = [c["content"] for c in chunk_data]
        embeddings = await embedding_service.embed_texts(texts)

        for i, cd in enumerate(chunk_data):
            chunk = Chunk(
                id=uuid.uuid4(),
                document_id=document.id,
                content=cd["content"],
                chunk_index=cd["chunk_index"],
                token_count=cd["token_count"],
                embedding=embeddings[i],
                created_at=datetime.utcnow(),
            )
            db.add(chunk)

        document.status = "ready"
        await db.flush()
        await db.refresh(document)
    except Exception as e:
        document.status = "failed"
        await db.flush()
        raise HTTPException(status_code=500, detail=f"Processing failed: {str(e)}")

    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        status=document.status,
        page_count=document.page_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("", response_model=DocumentListResponse)
async def list_documents(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
):
    stmt = (
        select(Document)
        .where(Document.user_id == current_user.id)
        .order_by(Document.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    documents = result.scalars().all()

    count_stmt = select(func.count(Document.id)).where(Document.user_id == current_user.id)
    count_result = await db.execute(count_stmt)
    total = count_result.scalar()

    return DocumentListResponse(
        documents=[
            DocumentResponse(
                id=d.id,
                filename=d.filename,
                file_type=d.file_type,
                file_size=d.file_size,
                status=d.status,
                page_count=d.page_count,
                created_at=d.created_at,
                updated_at=d.updated_at,
            )
            for d in documents
        ],
        total=total,
    )


@router.get("/{document_id}", response_model=DocumentResponse)
async def get_document(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    document = result.scalar_one_or_none()
    if not document:
        raise HTTPException(status_code=404, detail="Document not found")
    return DocumentResponse(
        id=document.id,
        filename=document.filename,
        file_type=document.file_type,
        file_size=document.file_size,
        status=document.status,
        page_count=document.page_count,
        created_at=document.created_at,
        updated_at=document.updated_at,
    )


@router.get("/{document_id}/chunks", response_model=ChunkListResponse)
async def get_document_chunks(
    document_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    doc_stmt = select(Document).where(
        Document.id == document_id,
        Document.user_id == current_user.id,
    )
    doc_result = await db.execute(doc_stmt)
    if not doc_result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")

    stmt = (
        select(Chunk)
        .where(Chunk.document_id == document_id)
        .order_by(Chunk.chunk_index.asc())
        .offset(skip)
        .limit(limit)
    )
    result = await db.execute(stmt)
    chunks = result.scalars().all()

    return ChunkListResponse(
        chunks=[
            ChunkResponse(
                id=c.id,
                document_id=c.document_id,
                content=c.content,
                chunk_index=c.chunk_index,
                token_count=c.token_count,
                has_embedding=c.embedding is not None,
                created_at=c.created_at,
            )
            for c in chunks
        ],
        total=len(chunks),
    )
