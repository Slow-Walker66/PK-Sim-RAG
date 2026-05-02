from __future__ import annotations

import hashlib
import re
from typing import Any, Dict, Iterable, List


def clean_for_chunk(text: str) -> str:
    text = (text or "").replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def clean_github_text(text: str) -> str:
    text = clean_for_chunk(text)
    if not text:
        return ""

    kept_lines = []
    skip_rest_markers = (
        "reply to this email directly",
        "you are receiving this because",
        "unsubscribe",
        "message id:",
    )
    noisy_prefixes = (
        "from:",
        "sent:",
        "to:",
        "cc:",
        "subject:",
        "caution:",
        "external email",
    )
    for line in text.splitlines():
        stripped = line.strip()
        lower = stripped.lower()
        if any(marker in lower for marker in skip_rest_markers):
            break
        if lower.startswith(noisy_prefixes):
            continue
        if "github.com/notifications/unsubscribe" in lower:
            break
        kept_lines.append(line)
    return clean_for_chunk("\n".join(kept_lines))


def truncate(text: str, limit: int = 1000) -> str:
    clean = clean_for_chunk(text)
    if len(clean) <= limit:
        return clean
    return clean[: limit - 3].rstrip() + "..."


def stable_hash(*parts: Any) -> str:
    h = hashlib.sha1()
    for part in parts:
        h.update(str(part).encode("utf-8", errors="ignore"))
        h.update(b"\x1f")
    return h.hexdigest()[:16]


def split_text(text: str, *, chunk_size: int = 1200, overlap: int = 180) -> List[str]:
    text = clean_for_chunk(text)
    if not text:
        return []
    if len(text) <= chunk_size:
        return [text]

    paragraphs = [p.strip() for p in re.split(r"\n\s*\n", text) if p.strip()]
    chunks: List[str] = []
    current = ""

    for paragraph in paragraphs:
        if len(paragraph) > chunk_size:
            if current:
                chunks.append(current.strip())
                current = ""
            start = 0
            while start < len(paragraph):
                end = start + chunk_size
                chunks.append(paragraph[start:end].strip())
                if end >= len(paragraph):
                    break
                start = max(0, end - overlap)
            continue

        candidate = f"{current}\n\n{paragraph}".strip() if current else paragraph
        if len(candidate) <= chunk_size:
            current = candidate
        else:
            chunks.append(current.strip())
            prefix = current[-overlap:].strip() if overlap and current else ""
            current = f"{prefix}\n\n{paragraph}".strip() if prefix else paragraph

    if current:
        chunks.append(current.strip())
    return [chunk for chunk in chunks if chunk]


def chunk_pdf_records(
    records: Iterable[dict],
    *,
    chunk_size: int = 1200,
    overlap: int = 180,
    window_pages: int = 1,
    window_stride: int = 1,
) -> List[dict]:
    chunks: List[dict] = []

    pages = sorted(
        [record for record in records if clean_for_chunk(record.get("text", ""))],
        key=lambda item: (item.get("file_name", ""), int(item.get("page_start", 0) or 0)),
    )
    if not pages:
        return chunks

    window_pages = max(1, window_pages)
    window_stride = max(1, window_stride)

    if window_pages == 1:
        for record in pages:
            text = clean_for_chunk(record.get("text", ""))
            file_name = record.get("file_name", "")
            page_start = int(record.get("page_start", 0) or 0)
            page_end = int(record.get("page_end", page_start) or page_start)
            section = record.get("section", "Unknown")
            for index, chunk_text in enumerate(split_text(text, chunk_size=chunk_size, overlap=overlap)):
                chunk_id = f"pdf:{stable_hash(file_name, page_start, page_end, index, chunk_text)}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": chunk_text,
                        "metadata": {
                            "source_type": "pdf",
                            "file_name": file_name,
                            "page_start": page_start,
                            "page_end": page_end,
                            "section": section,
                            "chunk_index": index,
                            "chunk_strategy": "single_page",
                        },
                    }
                )
        return chunks

    by_file: Dict[str, List[dict]] = {}
    for record in pages:
        by_file.setdefault(record.get("file_name", ""), []).append(record)

    for file_name, file_pages in by_file.items():
        for start in range(0, len(file_pages), window_stride):
            window = file_pages[start : start + window_pages]
            if not window:
                continue
            page_start = int(window[0].get("page_start", 0) or 0)
            page_end = int(window[-1].get("page_end", page_start) or page_start)
            section_values = []
            body_parts = []
            for page in window:
                section = page.get("section", "Unknown")
                if section and section not in section_values:
                    section_values.append(section)
                page_number = int(page.get("page_start", 0) or 0)
                page_text = clean_for_chunk(page.get("text", ""))
                body_parts.append(f"Page {page_number}\n{page_text}")
            section = " / ".join(section_values[:3]) or "Unknown"
            chunk_text = clean_for_chunk("\n\n".join(body_parts))
            chunk_id = f"pdf:{stable_hash(file_name, page_start, page_end, chunk_text)}"
            chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": {
                        "source_type": "pdf",
                        "file_name": file_name,
                        "page_start": page_start,
                        "page_end": page_end,
                        "section": section,
                        "chunk_index": start,
                        "chunk_strategy": f"{window_pages}_page_window",
                    },
                }
            )
    return chunks


def _discussion_question_text(discussion: Dict[str, Any]) -> str:
    title = discussion.get("title", "")
    body = clean_github_text(discussion.get("body_text", ""))
    return clean_for_chunk(f"{title}\n\n{body}")


def _github_metadata(
    discussion: Dict[str, Any],
    *,
    source_role: str,
    answer_summary: str = "",
    comment_url: str = "",
    comment_id: str = "",
    chunk_index: int = 0,
) -> dict:
    return {
        "source_type": "github_discussion",
        "discussion_number": discussion.get("number", ""),
        "title": discussion.get("title", ""),
        "url": discussion.get("url", ""),
        "comment_url": comment_url,
        "comment_id": comment_id,
        "category": discussion.get("category", ""),
        "source_role": source_role,
        "question_text": truncate(_discussion_question_text(discussion), 1400),
        "answer_summary": truncate(answer_summary, 1400),
        "chunk_index": chunk_index,
    }


def chunk_github_discussions(
    discussions: Iterable[dict],
    *,
    chunk_size: int = 1200,
    overlap: int = 180,
) -> List[dict]:
    chunks: List[dict] = []

    for discussion in discussions:
        question = _discussion_question_text(discussion)
        answer = discussion.get("answer") or {}
        accepted_answer_text = clean_github_text(answer.get("body_text", ""))
        comments = discussion.get("comments", []) or []

        question_context = (
            f"GitHub Discussion Title: {discussion.get('title', '')}\n\n"
            f"Original Question:\n{question}\n\n"
            f"Accepted Answer:\n{accepted_answer_text}"
        ).strip()

        for index, chunk_text in enumerate(split_text(question_context, chunk_size=chunk_size, overlap=overlap)):
            chunk_id = f"github:{stable_hash(discussion.get('id'), 'question', index, chunk_text)}"
            chunks.append(
                {
                    "id": chunk_id,
                    "text": chunk_text,
                    "metadata": _github_metadata(
                        discussion,
                        source_role="question",
                        answer_summary=accepted_answer_text,
                        comment_url=answer.get("url", ""),
                        comment_id=answer.get("id", ""),
                        chunk_index=index,
                    ),
                }
            )

        for comment in comments:
            comment_text = clean_github_text(comment.get("body_text", ""))
            if not comment_text:
                continue
            role = "accepted_answer" if comment.get("is_answer") else "comment"
            comment_context = (
                f"GitHub Discussion Title: {discussion.get('title', '')}\n\n"
                f"Original Question:\n{question}\n\n"
                f"Related Answer or Comment:\n{comment_text}"
            )
            for index, chunk_text in enumerate(split_text(comment_context, chunk_size=chunk_size, overlap=overlap)):
                chunk_id = f"github:{stable_hash(discussion.get('id'), comment.get('id'), index, chunk_text)}"
                chunks.append(
                    {
                        "id": chunk_id,
                        "text": chunk_text,
                        "metadata": _github_metadata(
                            discussion,
                            source_role=role,
                            answer_summary=comment_text,
                            comment_url=comment.get("url", ""),
                            comment_id=comment.get("id", ""),
                            chunk_index=index,
                        ),
                    }
                )

    return chunks
