import uuid
from typing import Optional
from datetime import datetime
from sqlalchemy import select, desc, func
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.chat import ChatMessage


class ChatHistoryService:
    """Stores and retrieves chat messages from PostgreSQL."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def add_message(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        role: str,
        content: str,
        document_id: Optional[uuid.UUID] = None,
        sources: Optional[list] = None,
    ) -> ChatMessage:
        message = ChatMessage(
            id=uuid.uuid4(),
            session_id=session_id,
            user_id=user_id,
            role=role,
            content=content,
            document_id=document_id,
            sources=sources,
            created_at=datetime.utcnow(),
        )
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message

    async def get_history(
        self,
        session_id: uuid.UUID,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[ChatMessage]:
        stmt = (
            select(ChatMessage)
            .where(
                ChatMessage.session_id == session_id,
                ChatMessage.user_id == user_id,
            )
            .order_by(ChatMessage.created_at.asc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        return result.scalars().all()

    async def get_user_sessions(
        self,
        user_id: uuid.UUID,
        limit: int = 50,
        offset: int = 0,
    ) -> list[dict]:
        """Get unique session IDs for a user with latest message preview."""
        subq = (
            select(
                ChatMessage.session_id,
                ChatMessage.created_at,
                func.row_number().over(
                    partition_by=ChatMessage.session_id,
                    order_by=ChatMessage.created_at.desc(),
                ).label("rn"),
                ChatMessage.content.label("preview"),
            )
            .where(ChatMessage.user_id == user_id)
            .subquery()
        )
        stmt = (
            select(
                subq.c.session_id,
                subq.c.created_at.label("last_message_at"),
                subq.c.preview,
            )
            .where(subq.c.rn == 1)
            .order_by(subq.c.created_at.desc())
            .offset(offset)
            .limit(limit)
        )
        result = await self.db.execute(stmt)
        rows = result.fetchall()
        return [
            {
                "session_id": str(row.session_id),
                "last_message_at": row.last_message_at,
                "preview": row.preview[:100] if row.preview else "",
            }
            for row in rows
        ]
