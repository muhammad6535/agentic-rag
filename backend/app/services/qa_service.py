"""Question-answering service.

Takes retrieved chunks and a user question, then uses an LLM to generate
an answer grounded strictly in the provided context.
This implements the "generation" phase of the RAG pipeline.
"""

from langchain_ollama import ChatOllama
from langchain.prompts import ChatPromptTemplate
from langchain.schema import StrOutputParser
from app.config import settings


SYSTEM_PROMPT = """You are an Enterprise Knowledge Assistant. Answer based ONLY on the context below.

Rules:
1. Use ONLY the provided context to answer.
2. Cite sources inline: [Source: document_name, Chunk X]
3. Be concise. If context lacks info, simply state what you know and note what is missing.
4. ALWAYS answer to the best of your ability from context. Never say you cannot answer if you already have relevant information.

Context:
{context}

Question: {question}

Answer:"""


class QAService:
    """Generates grounded answers using an LLM with retrieved context."""

    def __init__(self):
        self.llm = ChatOllama(
            model=settings.llm_model,
            base_url=settings.ollama_base_url,
            temperature=0,
        )
        self.prompt = ChatPromptTemplate.from_messages([
            ("system", SYSTEM_PROMPT),
            ("human", "{question}"),
        ])
        self.chain = self.prompt | self.llm | StrOutputParser()

    async def answer(self, question: str, chunks: list[dict]) -> str:
        """
        Generate an answer grounded in the retrieved chunks.

        Args:
            question: The user's question.
            chunks: Retrieved context chunks with content and metadata.

        Returns:
            The generated answer string.
        """
        context_parts = []
        for i, chunk in enumerate(chunks):
            doc_name = chunk.get("document_name", "Unknown")
            chunk_idx = chunk.get("chunk_index", 0)
            context_parts.append(
                f"[Source: {doc_name}, Chunk {chunk_idx}]\n{chunk['content']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        response = await self.chain.ainvoke({
            "context": context,
            "question": question,
        })
        return response

    async def answer_stream(self, question: str, chunks: list[dict]):
        """
        Stream a grounded answer from the LLM.

        Args:
            question: The user's question.
            chunks: Retrieved context chunks.

        Yields:
            Tokens of the generated answer.
        """
        context_parts = []
        for chunk in chunks:
            doc_name = chunk.get("document_name", "Unknown")
            chunk_idx = chunk.get("chunk_index", 0)
            context_parts.append(
                f"[Source: {doc_name}, Chunk {chunk_idx}]\n{chunk['content']}"
            )
        context = "\n\n---\n\n".join(context_parts)

        async for token in self.chain.astream({
            "context": context,
            "question": question,
        }):
            yield token
