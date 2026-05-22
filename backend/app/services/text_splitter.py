"""Text splitting service.

Breaks extracted document text into manageable chunks for embedding.
Uses LangChain's text splitters for intelligent chunking.
This is the second step in the ingestion pipeline.
"""

from langchain_text_splitters import RecursiveCharacterTextSplitter
from app.config import settings


class TextSplitterService:
    """Splits document text into chunks using recursive character splitting."""

    def __init__(self):
        self.splitter = RecursiveCharacterTextSplitter(
            chunk_size=settings.chunk_size,
            chunk_overlap=settings.chunk_overlap,
            length_function=len,
            separators=["\n\n", "\n", ". ", " ", ""],
        )

    def split_text(self, text: str) -> list[str]:
        """
        Split text into chunks.

        Args:
            text: The full document text.

        Returns:
            List of text chunks.
        """
        chunks = self.splitter.split_text(text)
        return chunks

    def split_with_metadata(self, text: str) -> list[dict]:
        """
        Split text and return chunks with metadata.

        Returns:
            List of dicts with 'content' and 'chunk_index' keys.
        """
        chunks = self.split_text(text)
        return [
            {"content": chunk, "chunk_index": i, "token_count": len(chunk.split())}
            for i, chunk in enumerate(chunks)
        ]
