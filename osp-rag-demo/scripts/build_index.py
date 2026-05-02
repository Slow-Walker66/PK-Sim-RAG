from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List

from tqdm import tqdm

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import settings
from rag.chunker import chunk_github_discussions, chunk_pdf_records
from rag.embeddings import EmbeddingModel
from rag.vector_store import ChromaVectorStore


def read_jsonl(path: Path) -> List[dict]:
    if not path.exists():
        return []
    rows = []
    with path.open("r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                rows.append(json.loads(line))
    return rows


def write_jsonl(path: Path, rows: Iterable[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for row in rows:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="Build Chroma vector index.")
    parser.add_argument(
        "--pdf-jsonl",
        default=str(PROJECT_DIR / "data/processed/pdf_pages.jsonl"),
        help="PDF pages JSONL.",
    )
    parser.add_argument(
        "--github-jsonl",
        default=str(PROJECT_DIR / "data/processed/github_discussions.jsonl"),
        help="GitHub discussions JSONL.",
    )
    parser.add_argument(
        "--chunks-output",
        default=str(PROJECT_DIR / "data/processed/chunks.jsonl"),
        help="Debug output for merged chunks.",
    )
    parser.add_argument("--reset", action="store_true", help="Reset collection before indexing.")
    parser.add_argument("--chunk-size", type=int, default=settings.chunk_size)
    parser.add_argument("--chunk-overlap", type=int, default=settings.chunk_overlap)
    parser.add_argument("--pdf-window-pages", type=int, default=settings.pdf_window_pages)
    parser.add_argument("--pdf-window-stride", type=int, default=settings.pdf_window_stride)
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    pdf_records = read_jsonl(Path(args.pdf_jsonl))
    github_records = read_jsonl(Path(args.github_jsonl))

    if not pdf_records and not github_records:
        raise SystemExit(
            "No processed data found. Run scripts/ingest_pdf.py and/or "
            "scripts/ingest_github_discussions.py first."
        )

    chunks = []
    chunks.extend(
        chunk_pdf_records(
            pdf_records,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap,
            window_pages=args.pdf_window_pages,
            window_stride=args.pdf_window_stride,
        )
    )
    chunks.extend(
        chunk_github_discussions(
            github_records,
            chunk_size=args.chunk_size,
            overlap=args.chunk_overlap,
        )
    )
    if not chunks:
        raise SystemExit("No chunks produced from processed data.")

    write_jsonl(Path(args.chunks_output), chunks)
    print(
        f"Prepared {len(chunks)} chunks "
        f"({len(pdf_records)} PDF pages, {len(github_records)} GitHub discussions, "
        f"PDF window={args.pdf_window_pages} pages)."
    )

    store = ChromaVectorStore(settings.vector_db_dir, settings.collection_name)
    if args.reset:
        store.reset()

    embedder = EmbeddingModel(settings.embedding_model, device=settings.embedding_device)
    for start in tqdm(range(0, len(chunks), args.batch_size), desc="Embedding and indexing"):
        batch = chunks[start : start + args.batch_size]
        texts = [item["text"] for item in batch]
        embeddings = embedder.encode(texts)
        store.upsert(
            ids=[item["id"] for item in batch],
            texts=texts,
            metadatas=[item["metadata"] for item in batch],
            embeddings=embeddings,
            batch_size=args.batch_size,
        )

    print(f"Indexed {store.count()} chunks into {settings.vector_db_dir}")


if __name__ == "__main__":
    main()
