from __future__ import annotations

import re
from dataclasses import dataclass, asdict
from pathlib import Path
from typing import Iterable, List

import fitz


HEADING_PATTERNS = [
    re.compile(r"^\d+(\.\d+)*\s+[A-Z][A-Za-z0-9 ,:/()\-]{3,}$"),
    re.compile(r"^[A-Z][A-Za-z0-9 ,:/()\-]{3,80}$"),
]


@dataclass
class PdfPage:
    file_name: str
    page_start: int
    page_end: int
    section: str
    text: str

    def to_dict(self) -> dict:
        return asdict(self)


def _clean_text(text: str) -> str:
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _looks_like_heading(line: str) -> bool:
    clean = line.strip()
    if not clean or len(clean) > 100:
        return False
    if clean.endswith(".") and len(clean.split()) > 6:
        return False
    return any(pattern.match(clean) for pattern in HEADING_PATTERNS)


def infer_section(text: str, previous_section: str = "") -> str:
    for line in text.splitlines()[:20]:
        line = line.strip()
        if _looks_like_heading(line):
            return line
    return previous_section or "Unknown"


def parse_pdf(pdf_path: str | Path, min_chars: int = 20) -> List[PdfPage]:
    path = Path(pdf_path)
    if not path.exists():
        raise FileNotFoundError(f"PDF not found: {path}")

    pages: List[PdfPage] = []
    current_section = "Unknown"
    with fitz.open(path) as doc:
        for page_index, page in enumerate(doc, start=1):
            text = _clean_text(page.get_text("text", sort=True))
            if len(text) < min_chars:
                continue
            current_section = infer_section(text, current_section)
            pages.append(
                PdfPage(
                    file_name=path.name,
                    page_start=page_index,
                    page_end=page_index,
                    section=current_section,
                    text=text,
                )
            )
    return pages


def pages_to_jsonl_rows(pages: Iterable[PdfPage]) -> Iterable[dict]:
    for page in pages:
        yield page.to_dict()

