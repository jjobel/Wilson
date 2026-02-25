"""Textbook PDF indexer using vector embeddings for RAG retrieval."""

from __future__ import annotations

import logging
from pathlib import Path

import chromadb
import pymupdf

logger = logging.getLogger(__name__)

# Target chunk size in characters (roughly 1-2 paragraphs)
CHUNK_SIZE = 1500
CHUNK_OVERLAP = 200


class TextbookIndexer:
    """Indexes textbook PDFs into a vector store for retrieval."""

    def __init__(self, persist_dir: str = "./data/vectors") -> None:
        self._client = chromadb.PersistentClient(path=persist_dir)
        self._collection = self._client.get_or_create_collection(
            name="textbooks",
            metadata={"hnsw:space": "cosine"},
        )

    def ingest_pdf(self, pdf_path: str, textbook_name: str | None = None) -> int:
        """Extract text from a PDF and index it into the vector store.

        Args:
            pdf_path: Path to the PDF file.
            textbook_name: Optional human-readable name for the textbook.

        Returns:
            Number of chunks indexed.
        """
        path = Path(pdf_path)
        if not path.exists():
            raise FileNotFoundError(f"PDF not found: {pdf_path}")

        name = textbook_name or path.stem
        logger.info("Ingesting textbook: %s (%s)", name, pdf_path)

        # Extract text from PDF
        doc = pymupdf.open(pdf_path)
        full_text = ""
        for page in doc:
            full_text += page.get_text() + "\n"
        doc.close()

        # Chunk the text
        chunks = self._chunk_text(full_text)
        if not chunks:
            logger.warning("No text extracted from %s", pdf_path)
            return 0

        # Add to vector store
        ids = [f"{name}__chunk_{i}" for i in range(len(chunks))]
        metadatas = [
            {"textbook": name, "chunk_index": i, "source_file": str(path.name)}
            for i in range(len(chunks))
        ]

        self._collection.upsert(
            ids=ids,
            documents=chunks,
            metadatas=metadatas,
        )

        logger.info("Indexed %d chunks from %s", len(chunks), name)
        return len(chunks)

    def query(self, question: str, n_results: int = 5) -> str:
        """Retrieve relevant textbook passages for a question.

        Args:
            question: The query to search for.
            n_results: Maximum number of passages to return.

        Returns:
            Formatted string of relevant textbook passages with source info.
        """
        results = self._collection.query(
            query_texts=[question],
            n_results=n_results,
        )

        if not results["documents"] or not results["documents"][0]:
            return ""

        passages = []
        for doc, meta in zip(results["documents"][0], results["metadatas"][0]):
            source = meta.get("textbook", "Unknown")
            passages.append(f"[{source}]\n{doc}")

        return "\n\n---\n\n".join(passages)

    def _chunk_text(self, text: str) -> list[str]:
        """Split text into overlapping chunks."""
        chunks = []
        start = 0
        while start < len(text):
            end = start + CHUNK_SIZE

            # Try to break at a paragraph or sentence boundary
            if end < len(text):
                # Look for paragraph break
                para_break = text.rfind("\n\n", start, end)
                if para_break > start + CHUNK_SIZE // 2:
                    end = para_break + 2
                else:
                    # Look for sentence break
                    sent_break = text.rfind(". ", start, end)
                    if sent_break > start + CHUNK_SIZE // 2:
                        end = sent_break + 2

            chunk = text[start:end].strip()
            if chunk:
                chunks.append(chunk)

            start = end - CHUNK_OVERLAP

        return chunks

    def list_textbooks(self) -> list[str]:
        """Return names of all indexed textbooks."""
        all_metadata = self._collection.get()["metadatas"]
        textbooks = set()
        for meta in all_metadata:
            if "textbook" in meta:
                textbooks.add(meta["textbook"])
        return sorted(textbooks)
