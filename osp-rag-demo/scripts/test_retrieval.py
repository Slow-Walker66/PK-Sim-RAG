from __future__ import annotations

import argparse
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import settings
from rag.embeddings import EmbeddingModel
from rag.prompts import INSUFFICIENT_MESSAGE
from rag.retriever import Retriever
from rag.vector_store import ChromaVectorStore


def main() -> None:
    parser = argparse.ArgumentParser(description="Test vector retrieval.")
    parser.add_argument("query", nargs="?", default="How to install Open Systems Pharmacology Suite?")
    parser.add_argument("--top-k", type=int, default=settings.top_k)
    parser.add_argument("--min-score", type=float, default=settings.min_relevance_score)
    args = parser.parse_args()

    store = ChromaVectorStore(settings.vector_db_dir, settings.collection_name)
    if store.count() == 0:
        raise SystemExit("Vector store is empty. Run scripts/build_index.py first.")

    retriever = Retriever(
        EmbeddingModel(settings.embedding_model, device=settings.embedding_device),
        store,
        pdf_pages_path=settings.pdf_pages_path,
        pdf_context_pages=settings.pdf_context_pages,
    )
    results = retriever.retrieve(args.query, top_k=args.top_k, min_score=args.min_score)
    if not results:
        print(INSUFFICIENT_MESSAGE)
        return

    print(f"Query: {args.query}")
    print(f"Results: {len(results)}")
    for index, item in enumerate(results, start=1):
        meta = item.metadata
        print("=" * 80)
        print(f"[S{index}] score={item.score:.3f} distance={item.distance:.3f}")
        if meta.get("source_type") == "pdf":
            print(
                f"PDF: {meta.get('file_name')} "
                f"page={meta.get('page_start')}-{meta.get('page_end')} "
                f"section={meta.get('section')}"
            )
        elif meta.get("source_type") == "github_discussion":
            print(f"GitHub: {meta.get('title')}")
            print(f"URL: {meta.get('comment_url') or meta.get('url')}")
            print(f"Question: {meta.get('question_text', '')[:500]}")
            print(f"Answer summary: {meta.get('answer_summary', '')[:500]}")
        print(item.text[:900].replace("\n", " "))


if __name__ == "__main__":
    main()
