import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.document import Document
from app.models.user import User
from app.schemas.chat import (
    AskRequest,
    AskResponse,
    SourceChunk,
    ChatHistoryResponse,
    ChatMessageResponse,
    SessionListResponse,
)
from app.services.retrieval_service import RetrievalService
from app.services.qa_service import QAService
from app.services.agentic_rag_service import AgenticRAGService
from app.services.chat_history_service import ChatHistoryService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/chat", tags=["chat"])


async def _validate_doc_access(doc_id: uuid.UUID | None, db, user_id: uuid.UUID):
    if doc_id is None:
        return
    stmt = select(Document).where(Document.id == doc_id, Document.user_id == user_id)
    result = await db.execute(stmt)
    if not result.scalar_one_or_none():
        raise HTTPException(status_code=404, detail="Document not found")


@router.post("/ask", response_model=AskResponse)
async def ask_question(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    doc_id = None
    if request.document_id:
        try:
            doc_id = uuid.UUID(request.document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_id format")
        await _validate_doc_access(doc_id, db, current_user.id)

    session_id = uuid.UUID(request.session_id) if request.session_id else uuid.uuid4()

    agentic = AgenticRAGService(db)
    result = await agentic.answer(
        question=request.question,
        document_id=str(doc_id) if doc_id else None,
        user_id=str(current_user.id),
    )

    answer_text = result["answer"]
    sources = result.get("sources", [])

    if not sources:
        answer_text = (
            "I could not find any relevant information in the uploaded documents "
            "to answer your question. Please try uploading more documents or rephrasing."
        )

    chat_service = ChatHistoryService(db)
    await chat_service.add_message(
        session_id=session_id,
        user_id=current_user.id,
        role="user",
        content=request.question,
        document_id=doc_id,
    )
    await chat_service.add_message(
        session_id=session_id,
        user_id=current_user.id,
        role="assistant",
        content=answer_text,
        document_id=doc_id,
        sources=sources or None,
    )

    return AskResponse(
        answer=answer_text,
        session_id=str(session_id),
        sources=[SourceChunk(**s) for s in sources] if sources else [],
    )


@router.post("/ask/stream")
async def ask_question_stream(
    request: AskRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    from fastapi.responses import StreamingResponse
    from app.database import async_session_factory

    doc_id = None
    if request.document_id:
        try:
            doc_id = uuid.UUID(request.document_id)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_id format")
        await _validate_doc_access(doc_id, db, current_user.id)

    session_id = uuid.UUID(request.session_id) if request.session_id else uuid.uuid4()

    agentic = AgenticRAGService(db)
    result = await agentic.answer(
        question=request.question,
        document_id=str(doc_id) if doc_id else None,
        user_id=str(current_user.id),
    )

    sources_data = result.get("sources", [])

    if not sources_data:
        async def no_results():
            yield "data: " + '{"answer":"I could not find relevant information.","sources":[]}' + "\n\n"
        return StreamingResponse(no_results(), media_type="text/event-stream")

    qa_service = QAService()

    async def generate():
        full_answer = ""
        try:
            async for token in qa_service.answer_stream(request.question, sources_data):
                full_answer += token
                yield f"data: {token}\n\n"
            import json
            yield f"data: [DONE]{json.dumps({'session_id': str(session_id), 'sources': sources_data})}\n\n"
        finally:
            async with async_session_factory() as stream_db:
                chat_service = ChatHistoryService(stream_db)
                await chat_service.add_message(
                    session_id=session_id,
                    user_id=current_user.id,
                    role="user",
                    content=request.question,
                    document_id=doc_id,
                )
                await chat_service.add_message(
                    session_id=session_id,
                    user_id=current_user.id,
                    role="assistant",
                    content=full_answer,
                    document_id=doc_id,
                    sources=sources_data,
                )
                await stream_db.commit()

    return StreamingResponse(generate(), media_type="text/event-stream")


@router.get("/history", response_model=ChatHistoryResponse)
async def get_chat_history(
    session_id: str = Query(..., description="Session UUID"),
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(100, ge=1, le=500),
    offset: int = Query(0, ge=0),
):
    try:
        sid = uuid.UUID(session_id)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid session_id format")

    chat_service = ChatHistoryService(db)
    messages = await chat_service.get_history(
        session_id=sid,
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )

    return ChatHistoryResponse(
        messages=[
            ChatMessageResponse(
                id=m.id,
                session_id=m.session_id,
                role=m.role,
                content=m.content,
                document_id=m.document_id,
                sources=m.sources,
                created_at=m.created_at,
            )
            for m in messages
        ],
        total=len(messages),
    )


@router.get("/sessions", response_model=SessionListResponse)
async def list_sessions(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
):
    chat_service = ChatHistoryService(db)
    sessions = await chat_service.get_user_sessions(
        user_id=current_user.id,
        limit=limit,
        offset=offset,
    )
    return SessionListResponse(sessions=sessions, total=len(sessions))
