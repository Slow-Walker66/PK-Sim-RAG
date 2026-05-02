from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import settings
from rag.pdf_parser import pages_to_jsonl_rows, parse_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse local PDF into JSONL pages.")
    parser.add_argument("--pdf", default=str(settings.pdf_path), help="PDF path.")
    parser.add_argument(
        "--output",
        default=str(PROJECT_DIR / "data/processed/pdf_pages.jsonl"),
        help="Output JSONL file.",
    )
    parser.add_argument("--min-chars", type=int, default=20, help="Skip pages shorter than this.")
    args = parser.parse_args()

    pages = parse_pdf(args.pdf, min_chars=args.min_chars)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)
    with output.open("w", encoding="utf-8") as f:
        for row in pages_to_jsonl_rows(pages):
            f.write(json.dumps(row, ensure_ascii=False) + "\n")

    print(f"Parsed {len(pages)} PDF pages -> {output}")


if __name__ == "__main__":
    main()

