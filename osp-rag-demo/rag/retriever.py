from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from rag.embeddings import EmbeddingModel
from rag.vector_store import ChromaVectorStore, VectorSearchResult


@dataclass
class RetrievedChunk:
    id: str
    text: str
    metadata: dict
    distance: float
    score: float


class Retriever:
    def __init__(
        self,
        embeddings: EmbeddingModel,
        vector_store: ChromaVectorStore,
        *,
        pdf_pages_path: str | Path | None = None,
        pdf_context_pages: int = 0,
    ):
        self.embeddings = embeddings
        self.vector_store = vector_store
        self.pdf_pages_path = Path(pdf_pages_path) if pdf_pages_path else None
        self.pdf_context_pages = max(0, int(pdf_context_pages or 0))
        self._pdf_pages: Optional[Dict[Tuple[str, int], dict]] = None

    def retrieve(
        self,
        query: str,
        *,
        top_k: int = 8,
        min_score: float = 0.35,
        where: Optional[dict] = None,
    ) -> List[RetrievedChunk]:
        query_vector = self.embeddings.encode([query])[0]
        raw_results: List[VectorSearchResult] = self.vector_store.query(
            query_embedding=query_vector,
            top_k=max(top_k * 4, top_k),
            where=where,
        )
        filtered = [
            RetrievedChunk(
                id=result.id,
                text=result.text,
                metadata=result.metadata,
                distance=result.distance,
                score=result.score,
            )
            for result in raw_results
            if result.score >= min_score
        ]
        expanded = [self._expand_pdf_context(chunk) for chunk in filtered]
        reranked = self._rerank(query, expanded)
        return self._dedupe(reranked)[:top_k]

    @staticmethod
    def _dedupe(chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        seen = set()
        unique: List[RetrievedChunk] = []
        for chunk in chunks:
            meta = chunk.metadata
            source_type = meta.get("source_type", "")
            if source_type == "pdf":
                key = (
                    source_type,
                    meta.get("file_name", ""),
                    meta.get("page_start", ""),
                    meta.get("page_end", ""),
                )
            elif source_type == "github_discussion":
                key = (
                    source_type,
                    meta.get("discussion_number", ""),
                    meta.get("comment_id", "") or meta.get("source_role", ""),
                    meta.get("chunk_index", ""),
                )
            else:
                key = (chunk.id,)
            if key in seen:
                continue
            seen.add(key)
            unique.append(chunk)
        return unique

    def _load_pdf_pages(self) -> Dict[Tuple[str, int], dict]:
        if self._pdf_pages is not None:
            return self._pdf_pages
        pages: Dict[Tuple[str, int], dict] = {}
        if self.pdf_pages_path and self.pdf_pages_path.exists():
            with self.pdf_pages_path.open("r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    row = json.loads(line)
                    file_name = row.get("file_name", "")
                    page = int(row.get("page_start", 0) or 0)
                    if file_name and page:
                        pages[(file_name, page)] = row
        self._pdf_pages = pages
        return pages

    def _expand_pdf_context(self, chunk: RetrievedChunk) -> RetrievedChunk:
        if self.pdf_context_pages <= 0:
            return chunk
        meta = chunk.metadata
        if meta.get("source_type") != "pdf":
            return chunk

        file_name = meta.get("file_name", "")
        page_start = int(meta.get("page_start", 0) or 0)
        page_end = int(meta.get("page_end", page_start) or page_start)
        if not file_name or not page_start:
            return chunk

        pages = self._load_pdf_pages()
        if not pages:
            return chunk

        context_start = max(1, page_start - self.pdf_context_pages)
        context_end = page_end + self.pdf_context_pages
        after_pages = []
        for page_number in range(page_start, context_end + 1):
            row = pages.get((file_name, page_number))
            if row:
                after_pages.append(row)
        before_pages = []
        for page_number in range(context_start, page_start):
            row = pages.get((file_name, page_number))
            if row:
                before_pages.append(row)
        selected = after_pages + before_pages
        if not selected:
            return chunk

        text_parts = []
        for row in after_pages:
            text_parts.append(f"Page {row.get('page_start')}\n{row.get('text', '').strip()}")
        if before_pages:
            text_parts.append("Previous page context")
            for row in before_pages:
                text_parts.append(f"Page {row.get('page_start')}\n{row.get('text', '').strip()}")
        text = "\n\n".join(text_parts)
        sections = []
        chronological = sorted(selected, key=lambda row: int(row.get("page_start", 0) or 0))
        for row in chronological:
            section = row.get("section", "")
            if section and section not in sections:
                sections.append(section)

        expanded_meta = dict(meta)
        expanded_meta["matched_page_start"] = page_start
        expanded_meta["matched_page_end"] = page_end
        expanded_meta["page_start"] = int(chronological[0].get("page_start", page_start) or page_start)
        expanded_meta["page_end"] = int(chronological[-1].get("page_end", page_end) or page_end)
        expanded_meta["section"] = " / ".join(sections[:3]) or meta.get("section", "")
        expanded_meta["expanded_context_pages"] = self.pdf_context_pages
        return RetrievedChunk(
            id=f"{chunk.id}:expanded",
            text=text,
            metadata=expanded_meta,
            distance=chunk.distance,
            score=chunk.score,
        )

    @staticmethod
    def _query_terms(query: str) -> List[str]:
        terms = re.findall(r"[a-zA-Z][a-zA-Z0-9\-]+|[\u4e00-\u9fff]{2,}", query.lower())
        stopwords = {
            "what",
            "which",
            "where",
            "when",
            "how",
            "does",
            "with",
            "from",
            "into",
            "they",
            "them",
            "their",
            "区别",
            "什么",
            "哪些",
            "哪三种",
        }
        return [term for term in terms if term not in stopwords and len(term) > 1]

    def _rerank(self, query: str, chunks: List[RetrievedChunk]) -> List[RetrievedChunk]:
        terms = self._query_terms(query)
        if not terms:
            return chunks

        english_terms = [term for term in terms if re.match(r"^[a-zA-Z]", term)]
        phrase_bonus_terms = []
        for left, right in zip(english_terms, english_terms[1:]):
            phrase_bonus_terms.append(f"{left} {right}")

        def score(chunk: RetrievedChunk) -> float:
            text = f"{chunk.text} {chunk.metadata.get('title', '')} {chunk.metadata.get('section', '')}".lower()
            overlap = sum(1 for term in set(terms) if term in text)
            phrase_bonus = sum(1 for phrase in phrase_bonus_terms if phrase in text)
            return chunk.score + (0.035 * overlap) + (0.06 * phrase_bonus)

        return sorted(chunks, key=score, reverse=True)
