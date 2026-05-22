"""Embedding service.

Converts text chunks into vector embeddings using Ollama's local models.
This is the third step in the ingestion pipeline and is also used during retrieval.
"""

from langchain_ollama import OllamaEmbeddings
from app.config import settings


class EmbeddingService:
    """Generates vector embeddings for text chunks using LangChain + Ollama."""

    def __init__(self):
        self.embeddings_model = OllamaEmbeddings(
            model=settings.embedding_model,
            base_url=settings.ollama_base_url,
        )

    async def embed_texts(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for a list of texts.

        Args:
            texts: List of text strings to embed.

        Returns:
            List of embedding vectors (each is a list of floats).
        """
        embeddings = await self.embeddings_model.aembed_documents(texts)
        return embeddings

    async def embed_query(self, query: str) -> list[float]:
        """
        Generate an embedding for a query string.

        Args:
            query: The user's question.

        Returns:
            A single embedding vector.
        """
        embedding = await self.embeddings_model.aembed_query(query)
        return embedding
