import uuid
from datetime import datetime
from typing import Optional
from pydantic import BaseModel


class EvalRunRequest(BaseModel):
    question: str
    document_id: Optional[str] = None


class ClaimItem(BaseModel):
    claim: str
    supported: bool
    evidence: Optional[str] = None


class EvalRunResponse(BaseModel):
    id: uuid.UUID
    question: str
    answer: str
    document_name: Optional[str] = None
    faithfulness_score: float
    answer_relevance_score: float
    context_relevance_score: float
    hallucination_score: float
    overall_score: float
    supported_claims: list[ClaimItem]
    unsupported_claims: list[ClaimItem]
    sources_used: list[dict]
    created_at: datetime


class EvalHistoryResponse(BaseModel):
    evaluations: list[EvalRunResponse]
    total: int


class EvalSummaryResponse(BaseModel):
    total_evaluations: int
    avg_faithfulness: float
    avg_answer_relevance: float
    avg_context_relevance: float
    avg_hallucination: float
    avg_overall: float
    recent_evaluations: list[EvalRunResponse]
