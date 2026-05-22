"""Agentic RAG service.

Enhances the basic RAG pipeline with:
1. Query rewriting — generates search-optimized query variants
2. Multi-query retrieval — runs multiple queries, merges results via RRF
3. Reranking — LLM-based relevance scoring against original question
4. Self-reflection — verifies answer completeness and iterates if needed
"""

import json
import re
from typing import Optional
from sqlalchemy.ext.asyncio import AsyncSession
from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser

from app.config import settings
from app.services.retrieval_service import RetrievalService
from app.services.qa_service import QAService


QUERY_REWRITE_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are a search query optimizer. Given a user's question, generate 3 different versions optimized for semantic search.

Each version should:
- Rephrase the core intent using different vocabulary
- Be concise (10-20 words each)
- Cover different angles of the question

Return ONLY a JSON array of strings, no other text.
Example: ["What is RAG architecture?", "How does retrieval augmented generation work?", "Explain RAG system components"]"""),
    ("human", "Original question: {question}")
])

REFLECTION_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """You are an answer quality auditor. Given a user question, the generated answer, and the source context, evaluate if the answer is complete and accurate.

Check:
1. Does the answer directly address the question?
2. Are all claims supported by the provided context?
3. Is any important information from context missing?

Return JSON:
{"is_complete": true/false, "missing_info": "what's missing or empty string", "follow_up_query": "a search query to find missing info or empty string"}"""),
    ("human", """Question: {question}

Answer: {answer}

Context: {context}

Evaluation:""")
])


class AgenticRAGService:
    """Agentic RAG with query rewriting, multi-query retrieval, reranking, and self-reflection."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0.1,
        )
        self.rewrite_chain = QUERY_REWRITE_PROMPT | self.llm | StrOutputParser()
        self.reflection_chain = REFLECTION_PROMPT | self.llm | StrOutputParser()
        self.retrieval_service = RetrievalService(db)
        self.qa_service = QAService()

    async def answer(
        self,
        question: str,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
        max_iterations: int = 2,
    ) -> dict:
        """Run the full agentic RAG pipeline.

        Returns:
            dict with "answer", "sources", "iterations", "queries_used"
        """
        all_sources = []
        queries_used = [question]

        # Step 1: Query rewriting
        rewritten = await self._rewrite_queries(question)
        all_queries = [question] + rewritten[:2]  # original + 2 variants

        # Step 2: Multi-query retrieval + RRF merge
        for q in all_queries:
            chunks = await self.retrieval_service.retrieve(
                query=q,
                document_id=document_id,
                user_id=user_id,
                top_k=settings.top_k_retrieval,
            )
            all_sources.extend(chunks)
            if q != question:
                queries_used.append(q)

        # Deduplicate by chunk id, keep highest score
        seen = {}
        for c in all_sources:
            cid = c["id"]
            if cid not in seen or c["score"] > seen[cid]["score"]:
                seen[cid] = c
        merged = sorted(seen.values(), key=lambda x: x["score"], reverse=True)
        merged = merged[:settings.top_k_retrieval * 2]

        # Step 3: Rerank against original question
        reranked = await self._rerank(merged, question)

        # Step 4: Generate answer
        context = self._format_context(reranked)
        answer = await self.qa_service.answer(question, reranked)

        # Step 5: Self-reflection loop
        iterations = 1
        follow_up_queries = []

        for _ in range(max_iterations - 1):
            reflection = await self._reflect(question, answer, context)
            if reflection.get("is_complete"):
                break

            follow_up = reflection.get("follow_up_query", "")
            if not follow_up:
                break

            follow_up_queries.append(follow_up)
            extra = await self.retrieval_service.retrieve(
                query=follow_up,
                document_id=document_id,
                user_id=user_id,
                top_k=2,
            )
            seen2 = {c["id"] for c in reranked}
            new_chunks = [c for c in extra if c["id"] not in seen2]
            if not new_chunks:
                break

            reranked.extend(new_chunks)
            reranked = sorted(reranked, key=lambda x: x["score"], reverse=True)
            reranked = reranked[:settings.top_k_retrieval * 2]
            context = self._format_context(reranked)
            answer = await self.qa_service.answer(question, reranked)
            iterations += 1

        return {
            "answer": answer,
            "sources": [
                {
                    "id": c["id"],
                    "content": c["content"],
                    "document_name": c["document_name"],
                    "chunk_index": c["chunk_index"],
                    "score": c["score"],
                }
                for c in reranked
            ],
            "iterations": iterations,
            "queries_used": queries_used + follow_up_queries,
        }

    def _format_context(self, chunks: list[dict]) -> str:
        parts = []
        for c in chunks:
            doc_name = c.get("document_name", "Unknown")
            chunk_idx = c.get("chunk_index", 0)
            parts.append(f"[Source: {doc_name}, Chunk {chunk_idx}]\n{c['content']}")
        return "\n\n---\n\n".join(parts)

    async def _rewrite_queries(self, question: str) -> list[str]:
        try:
            raw = await self.rewrite_chain.ainvoke({"question": question})
            parsed = self._parse_json(raw, [])
            if isinstance(parsed, list) and len(parsed) > 0:
                return [str(s).strip() for s in parsed[:3]]
        except Exception:
            pass
        return []

    async def _rerank(self, chunks: list[dict], question: str) -> list[dict]:
        """Rerank chunks by relevance to the question using a simple prompt."""
        if len(chunks) <= 1:
            return chunks

        # Deduplicate by id
        seen = {}
        for c in chunks:
            seen[c["id"]] = c
        unique = list(seen.values())

        scored = []
        for c in unique:
            score = await self._score_relevance(question, c["content"])
            scored.append((c, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [c for c, _ in scored]

    async def _score_relevance(self, question: str, content: str) -> float:
        """Score a chunk's relevance to the question (0-1)."""
        prompt = ChatPromptTemplate.from_messages([
            ("system", "Rate relevance of the chunk to the question from 0.0 (irrelevant) to 1.0 (highly relevant). Return ONLY a number like 0.85."),
            ("human", f"Question: {question}\n\nChunk: {content[:500]}\n\nRelevance score:")
        ])
        try:
            raw = await (prompt | self.llm | StrOutputParser()).ainvoke({})
            match = re.search(r"(\d+\.?\d*)", raw.strip())
            if match:
                val = float(match.group(1))
                return max(0.0, min(1.0, val))
        except Exception:
            pass
        return 0.5

    async def _reflect(self, question: str, answer: str, context: str) -> dict:
        try:
            raw = await self.reflection_chain.ainvoke({
                "question": question,
                "answer": answer,
                "context": context,
            })
            return self._parse_json(raw, {"is_complete": True, "missing_info": "", "follow_up_query": ""})
        except Exception:
            return {"is_complete": True, "missing_info": "", "follow_up_query": ""}

    def _parse_json(self, raw: str, default):
        cleaned = re.sub(r'```(?:json)?\s*', '', raw).strip()
        match = re.search(r'(\{.*\}|\[.*\])', cleaned, re.DOTALL)
        if match:
            try:
                return json.loads(match.group(1))
            except json.JSONDecodeError:
                pass
        return default
