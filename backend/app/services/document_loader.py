"""Document loading service.

Handles extracting text from uploaded PDF and TXT files.
This is the first step in the ingestion pipeline.
"""

import os
from typing import Optional
from pypdf import PdfReader


class DocumentLoader:
    """Loads and extracts text content from uploaded documents."""

    SUPPORTED_EXTENSIONS = {".pdf", ".txt"}

    @staticmethod
    def extract_text(file_path: str) -> tuple[str, Optional[int]]:
        """
        Extract text content from a file.

        Args:
            file_path: Absolute path to the uploaded file.

        Returns:
            Tuple of (extracted_text, page_count_or_None).

        Raises:
            ValueError: If the file type is unsupported or file not found.
        """
        if not os.path.exists(file_path):
            raise ValueError(f"File not found: {file_path}")

        ext = os.path.splitext(file_path)[1].lower()
        if ext not in DocumentLoader.SUPPORTED_EXTENSIONS:
            raise ValueError(f"Unsupported file type: {ext}. Supported: {DocumentLoader.SUPPORTED_EXTENSIONS}")

        if ext == ".pdf":
            return DocumentLoader._extract_pdf(file_path)
        elif ext == ".txt":
            return DocumentLoader._extract_txt(file_path)
        else:
            raise ValueError(f"Unexpected file type: {ext}")

    @staticmethod
    def _extract_pdf(file_path: str) -> tuple[str, int]:
        """Extract text from a PDF using PyPDF2."""
        reader = PdfReader(file_path)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        full_text = "\n\n".join(pages)
        return full_text, len(reader.pages)

    @staticmethod
    def _extract_txt(file_path: str) -> tuple[str, None]:
        """Extract text from a plain text file."""
        with open(file_path, "r", encoding="utf-8", errors="replace") as f:
            text = f.read()
        return text, None
