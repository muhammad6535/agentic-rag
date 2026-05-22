from typing import Optional
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession
from app.config import settings
from app.services.embedding_service import EmbeddingService


class RetrievalService:
    """Retrieves relevant chunks from pgvector based on semantic similarity."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.embedding_service = EmbeddingService()

    async def retrieve(
        self,
        query: str,
        top_k: int = None,
        document_id: Optional[str] = None,
        user_id: Optional[str] = None,
    ) -> list[dict]:
        if top_k is None:
            top_k = settings.top_k_retrieval

        query_embedding = await self.embedding_service.embed_query(query)
        embed_str = "[" + ",".join(str(x) for x in query_embedding) + "]"

        filters = []
        params: dict = {"top_k": top_k}

        if document_id:
            filters.append("c.document_id = :document_id")
            params["document_id"] = document_id

        if user_id:
            filters.append("d.user_id = :user_id")
            params["user_id"] = user_id

        where_clause = " AND ".join(filters) if filters else "TRUE"

        sql = text(f"""
            SELECT
                c.id,
                c.content,
                c.chunk_index,
                c.document_id,
                c.token_count,
                d.filename as document_name,
                COALESCE(c.embedding <=> CAST(:embedding AS vector), 1.0) as distance
            FROM chunks c
            JOIN documents d ON d.id = c.document_id
            WHERE c.embedding IS NOT NULL AND {where_clause}
            ORDER BY COALESCE(c.embedding <=> CAST(:embedding AS vector), 1.0)
            LIMIT :top_k
        """)
        params["embedding"] = embed_str

        result = await self.db.execute(sql, params)
        rows = result.fetchall()

        chunks = []
        for row in rows:
            chunks.append({
                "id": str(row.id),
                "content": row.content,
                "chunk_index": row.chunk_index,
                "document_id": str(row.document_id),
                "document_name": row.document_name,
                "token_count": row.token_count,
                "score": float(1 - row.distance),
            })

        return chunks
