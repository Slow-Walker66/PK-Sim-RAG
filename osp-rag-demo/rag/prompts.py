from __future__ import annotations

from typing import Iterable

from rag.retriever import RetrievedChunk


INSUFFICIENT_MESSAGE = "当前知识库暂无足够相关内容"


SYSTEM_PROMPT = f"""
You are a private RAG assistant for Open Systems Pharmacology Suite.

Rules:
1. Answer only from the retrieved context supplied by the user message.
2. If the context is not sufficient to answer, reply exactly: {INSUFFICIENT_MESSAGE}
3. Match the language of the user's question. Chinese question -> Chinese answer. English question -> English answer.
4. Preserve original English reference excerpts verbatim when citing or summarizing evidence.
5. Cite sources with bracket markers like [S1], [S2]. Every factual claim should be traceable to a source marker.
6. Do not use outside knowledge, do not guess, and do not invent references.
7. When the context is sufficient, include a short "参考摘录" section for Chinese answers or "Reference excerpts" section for English answers. Keep excerpts in their original language, especially English text. Do not translate excerpts.
""".strip()


def _source_label(index: int, chunk: RetrievedChunk) -> str:
    meta = chunk.metadata
    if meta.get("source_type") == "pdf":
        pages = str(meta.get("page_start", ""))
        if meta.get("page_end") and meta.get("page_end") != meta.get("page_start"):
            pages = f"{meta.get('page_start')}-{meta.get('page_end')}"
        return f"[S{index}] PDF: {meta.get('file_name', '')}, page {pages}, section: {meta.get('section', '')}"

    if meta.get("source_type") == "github_discussion":
        link = meta.get("comment_url") or meta.get("url") or ""
        return f"[S{index}] GitHub Discussion: {meta.get('title', '')}, {link}"

    return f"[S{index}] Source"


def format_retrieved_context(chunks: Iterable[RetrievedChunk], max_chars: int = 12000) -> str:
    parts = []
    used_chars = 0
    per_source_limit = min(6500, max(2500, max_chars // 3))
    for index, chunk in enumerate(chunks, start=1):
        meta = chunk.metadata
        source = _source_label(index, chunk)
        text = chunk.text.strip()
        if len(text) > per_source_limit:
            text = text[: per_source_limit - 80].rstrip() + "\n[Excerpt truncated; see source pages for full context.]"
        question = meta.get("question_text", "")
        answer = meta.get("answer_summary", "")

        block = f"{source}\nScore: {chunk.score:.3f}\n"
        if question:
            block += f"Original question:\n{question}\n"
        if answer:
            block += f"Relevant answer summary or excerpt:\n{answer}\n"
        block += f"Reference excerpt:\n{text}\n"

        if used_chars + len(block) > max_chars:
            remaining = max_chars - used_chars
            if remaining <= 0:
                break
            block = block[:remaining]
        parts.append(block)
        used_chars += len(block)
        if used_chars >= max_chars:
            break
    return "\n\n---\n\n".join(parts)


def build_messages(question: str, chunks: Iterable[RetrievedChunk], *, max_context_chars: int) -> list[dict]:
    context = format_retrieved_context(chunks, max_context_chars)
    user_prompt = f"""
User question:
{question}

Retrieved context:
{context}

Write the final answer now. Remember: only use the retrieved context, match the user's language, cite with [S#], and include original-language reference excerpts in a final excerpt section.
""".strip()
    return [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": user_prompt},
    ]
