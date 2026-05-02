from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv


PROJECT_DIR = Path(__file__).resolve().parent


def _load_env_file() -> Optional[Path]:
    raw_candidates = [
        PROJECT_DIR.parent / ".env",
        PROJECT_DIR / ".env",
        Path.cwd() / ".env",
    ]
    candidates = []
    seen = set()
    for candidate in raw_candidates:
        resolved = candidate.resolve()
        if resolved not in seen:
            seen.add(resolved)
            candidates.append(candidate)

    loaded = []
    for candidate in candidates:
        if candidate.exists():
            load_dotenv(candidate, override=True)
            loaded.append(candidate)
    if loaded:
        return loaded[-1]
    load_dotenv(override=False)
    return None


ENV_FILE = _load_env_file()
ENV_DIR = ENV_FILE.parent if ENV_FILE else PROJECT_DIR


def _env(name: str, default: str = "") -> str:
    return os.getenv(name, default).strip()


def _env_int(name: str, default: int) -> int:
    value = _env(name)
    return int(value) if value else default


def _env_float(name: str, default: float) -> float:
    value = _env(name)
    return float(value) if value else default


def _resolve_path(value: str, default: str, *, prefer_existing: bool = False) -> Path:
    raw = value or default
    path = Path(raw).expanduser()
    if path.is_absolute():
        return path

    candidates = [
        PROJECT_DIR / path,
        ENV_DIR / path,
        Path.cwd() / path,
    ]
    if prefer_existing:
        for candidate in candidates:
            if candidate.exists():
                return candidate
    return candidates[0]


@dataclass(frozen=True)
class Settings:
    deepseek_api_key: str
    deepseek_base_url: str
    deepseek_model: str
    github_token: str
    github_owner: str
    github_repo: str
    pdf_path: Path
    pdf_pages_path: Path
    vector_db_dir: Path
    collection_name: str
    embedding_model: str
    embedding_device: str
    top_k: int
    min_relevance_score: float
    chunk_size: int
    chunk_overlap: int
    pdf_window_pages: int
    pdf_window_stride: int
    pdf_context_pages: int
    max_context_chars: int


def get_settings() -> Settings:
    return Settings(
        deepseek_api_key=_env("DEEPSEEK_API_KEY"),
        deepseek_base_url=_env("DEEPSEEK_BASE_URL", "https://api.deepseek.com/v1"),
        deepseek_model=_env("DEEPSEEK_MODEL", "deepseek-chat"),
        github_token=_env("GITHUB_TOKEN"),
        github_owner=_env("GITHUB_OWNER", "Open-Systems-Pharmacology"),
        github_repo=_env("GITHUB_REPO", "Forum"),
        pdf_path=_resolve_path(
            _env("PDF_PATH"),
            "data/raw/Open Systems Pharmacology Suite.pdf",
            prefer_existing=True,
        ),
        pdf_pages_path=_resolve_path(_env("PDF_PAGES_PATH"), "data/processed/pdf_pages.jsonl"),
        vector_db_dir=_resolve_path(_env("VECTOR_DB_DIR"), "storage/chroma"),
        collection_name=_env("COLLECTION_NAME", "osp_knowledge_base"),
        embedding_model=_env("EMBEDDING_MODEL", "BAAI/bge-m3"),
        embedding_device=_env("EMBEDDING_DEVICE", ""),
        top_k=_env_int("TOP_K", 8),
        min_relevance_score=_env_float("MIN_RELEVANCE_SCORE", 0.70),
        chunk_size=_env_int("CHUNK_SIZE", 1200),
        chunk_overlap=_env_int("CHUNK_OVERLAP", 180),
        pdf_window_pages=_env_int("PDF_WINDOW_PAGES", 1),
        pdf_window_stride=_env_int("PDF_WINDOW_STRIDE", 1),
        pdf_context_pages=_env_int("PDF_CONTEXT_PAGES", 4),
        max_context_chars=_env_int("MAX_CONTEXT_CHARS", 18000),
    )


settings = get_settings()
