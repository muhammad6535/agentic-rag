import uuid
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select, func, desc
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models.evaluation import EvaluationResult
from app.models.user import User
from app.schemas.evaluation import (
    EvalRunRequest,
    EvalRunResponse,
    EvalHistoryResponse,
    EvalSummaryResponse,
    ClaimItem,
)
from app.services.retrieval_service import RetrievalService
from app.services.qa_service import QAService
from app.services.evaluation_service import EvaluationService
from app.services.auth_service import get_current_user

router = APIRouter(prefix="/evaluate", tags=["evaluation"])


@router.post("/run", response_model=EvalRunResponse)
async def run_evaluation(
    request: EvalRunRequest,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Run the full RAG evaluation pipeline:

    1. Retrieve relevant chunks for the question
    2. Generate an answer using the RAG pipeline
    3. Evaluate: faithfulness, hallucination, answer relevance, context relevance
    4. Store results in the database
    5. Return all metrics with claim-level detail
    """
    doc_id = None
    doc_name = None
    if request.document_id:
        try:
            doc_id = uuid.UUID(request.document_id)
            from sqlalchemy import select as sel
            from app.models.document import Document
            stmt = sel(Document).where(Document.id == doc_id, Document.user_id == current_user.id)
            result = await db.execute(stmt)
            doc = result.scalar_one_or_none()
            if not doc:
                raise HTTPException(status_code=404, detail="Document not found")
            doc_name = doc.filename
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid document_id format")

    # Step 1: Retrieve
    retrieval_service = RetrievalService(db)
    chunks = await retrieval_service.retrieve(
        query=request.question,
        document_id=doc_id,
        user_id=str(current_user.id),
    )

    if not chunks:
        return EvalRunResponse(
            id=uuid.uuid4(),
            question=request.question,
            answer="No relevant documents found.",
            document_name=doc_name,
            faithfulness_score=0.0,
            answer_relevance_score=0.0,
            context_relevance_score=0.0,
            hallucination_score=0.0,
            overall_score=0.0,
            supported_claims=[],
            unsupported_claims=[],
            sources_used=[],
            created_at=datetime.utcnow(),
        )

    # Step 2: Generate answer
    qa_service = QAService()
    answer = await qa_service.answer(request.question, chunks)

    # Step 3: Evaluate
    eval_service = EvaluationService()
    result = await eval_service.evaluate_full(request.question, answer, chunks)

    # Step 4: Store
    eval_record = EvaluationResult(
        id=uuid.uuid4(),
        user_id=current_user.id,
        question=request.question,
        answer=answer,
        document_id=doc_id,
        document_name=doc_name,
        faithfulness_score=result["faithfulness_score"],
        answer_relevance_score=result["answer_relevance_score"],
        context_relevance_score=result["context_relevance_score"],
        hallucination_score=result["hallucination_score"],
        overall_score=result["overall_score"],
        supported_claims=result["supported_claims"],
        unsupported_claims=result["unsupported_claims"],
        sources_used=[
            {
                "id": c["id"],
                "document_name": c["document_name"],
                "chunk_index": c["chunk_index"],
                "content_preview": c["content"][:200],
                "score": c["score"],
            }
            for c in chunks
        ],
        created_at=datetime.utcnow(),
    )
    db.add(eval_record)
    await db.flush()
    await db.refresh(eval_record)

    return EvalRunResponse(
        id=eval_record.id,
        question=eval_record.question,
        answer=eval_record.answer,
        document_name=eval_record.document_name,
        faithfulness_score=eval_record.faithfulness_score,
        answer_relevance_score=eval_record.answer_relevance_score,
        context_relevance_score=eval_record.context_relevance_score,
        hallucination_score=eval_record.hallucination_score,
        overall_score=eval_record.overall_score,
        supported_claims=[
            ClaimItem(**c) if isinstance(c, dict) else c
            for c in (result["supported_claims"] or [])
        ],
        unsupported_claims=[
            ClaimItem(**c) if isinstance(c, dict) else c
            for c in (result["unsupported_claims"] or [])
        ],
        sources_used=[
            {
                "id": s["id"],
                "document_name": s["document_name"],
                "chunk_index": s["chunk_index"],
                "content_preview": s.get("content_preview", s.get("content", ""))[:200],
                "score": s["score"],
            }
            for s in (result.get("sources_used", chunks))
        ],
        created_at=eval_record.created_at,
    )


@router.get("/history", response_model=EvalHistoryResponse)
async def get_eval_history(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
    limit: int = Query(20, ge=1, le=100),
    offset: int = Query(0, ge=0),
):
    """Get evaluation history for the current user."""
    stmt = (
        select(EvaluationResult)
        .where(EvaluationResult.user_id == current_user.id)
        .order_by(desc(EvaluationResult.created_at))
        .offset(offset)
        .limit(limit)
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    count_stmt = select(func.count(EvaluationResult.id)).where(
        EvaluationResult.user_id == current_user.id
    )
    total = (await db.execute(count_stmt)).scalar()

    return EvalHistoryResponse(
        evaluations=[
            EvalRunResponse(
                id=r.id,
                question=r.question,
                answer=r.answer,
                document_name=r.document_name,
                faithfulness_score=r.faithfulness_score,
                answer_relevance_score=r.answer_relevance_score,
                context_relevance_score=r.context_relevance_score,
                hallucination_score=r.hallucination_score,
                overall_score=r.overall_score,
                supported_claims=[
                    ClaimItem(**c) if isinstance(c, dict) else c
                    for c in (r.supported_claims or [])
                ],
                unsupported_claims=[
                    ClaimItem(**c) if isinstance(c, dict) else c
                    for c in (r.unsupported_claims or [])
                ],
                sources_used=r.sources_used or [],
                created_at=r.created_at,
            )
            for r in records
        ],
        total=total or 0,
    )


@router.get("/summary", response_model=EvalSummaryResponse)
async def get_eval_summary(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get aggregate evaluation summary for the current user."""
    stmt = (
        select(EvaluationResult)
        .where(EvaluationResult.user_id == current_user.id)
        .order_by(desc(EvaluationResult.created_at))
    )
    result = await db.execute(stmt)
    records = result.scalars().all()

    if not records:
        return EvalSummaryResponse(
            total_evaluations=0,
            avg_faithfulness=0.0,
            avg_answer_relevance=0.0,
            avg_context_relevance=0.0,
            avg_hallucination=0.0,
            avg_overall=0.0,
            recent_evaluations=[],
        )

    n = len(records)
    recent = records[:5]

    return EvalSummaryResponse(
        total_evaluations=n,
        avg_faithfulness=round(sum(r.faithfulness_score for r in records) / n, 4),
        avg_answer_relevance=round(sum(r.answer_relevance_score for r in records) / n, 4),
        avg_context_relevance=round(sum(r.context_relevance_score for r in records) / n, 4),
        avg_hallucination=round(sum(r.hallucination_score for r in records) / n, 4),
        avg_overall=round(sum(r.overall_score for r in records) / n, 4),
        recent_evaluations=[
            EvalRunResponse(
                id=r.id,
                question=r.question,
                answer=r.answer,
                document_name=r.document_name,
                faithfulness_score=r.faithfulness_score,
                answer_relevance_score=r.answer_relevance_score,
                context_relevance_score=r.context_relevance_score,
                hallucination_score=r.hallucination_score,
                overall_score=r.overall_score,
                supported_claims=[
                    ClaimItem(**c) if isinstance(c, dict) else c
                    for c in (r.supported_claims or [])
                ],
                unsupported_claims=[
                    ClaimItem(**c) if isinstance(c, dict) else c
                    for c in (r.unsupported_claims or [])
                ],
                sources_used=r.sources_used or [],
                created_at=r.created_at,
            )
            for r in recent
        ],
    )


@router.get("/{eval_id}", response_model=EvalRunResponse)
async def get_evaluation_detail(
    eval_id: uuid.UUID,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Get a single evaluation result with full detail."""
    stmt = select(EvaluationResult).where(
        EvaluationResult.id == eval_id,
        EvaluationResult.user_id == current_user.id,
    )
    result = await db.execute(stmt)
    r = result.scalar_one_or_none()
    if not r:
        raise HTTPException(status_code=404, detail="Evaluation not found")

    return EvalRunResponse(
        id=r.id,
        question=r.question,
        answer=r.answer,
        document_name=r.document_name,
        faithfulness_score=r.faithfulness_score,
        answer_relevance_score=r.answer_relevance_score,
        context_relevance_score=r.context_relevance_score,
        hallucination_score=r.hallucination_score,
        overall_score=r.overall_score,
        supported_claims=[
            ClaimItem(**c) if isinstance(c, dict) else c
            for c in (r.supported_claims or [])
        ],
        unsupported_claims=[
            ClaimItem(**c) if isinstance(c, dict) else c
            for c in (r.unsupported_claims or [])
        ],
        sources_used=r.sources_used or [],
        created_at=r.created_at,
    )
