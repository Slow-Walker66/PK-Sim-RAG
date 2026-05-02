from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[1]


def run_step(args: list[str]) -> None:
    print(f"\n$ {' '.join(args)}")
    subprocess.run(args, cwd=PROJECT_DIR, check=True)


def main() -> None:
    parser = argparse.ArgumentParser(description="Refresh local PDF/GitHub data and rebuild index.")
    parser.add_argument("--full-github", action="store_true", help="Fetch all GitHub discussions.")
    parser.add_argument("--skip-pdf", action="store_true", help="Skip PDF parsing.")
    parser.add_argument("--batch-size", type=int, default=32)
    args = parser.parse_args()

    python = sys.executable
    if not args.skip_pdf:
        run_step([python, "scripts/ingest_pdf.py"])

    github_args = [python, "scripts/ingest_github_discussions.py"]
    if args.full_github:
        github_args.append("--all")
    else:
        github_args.append("--since-existing")
    run_step(github_args)

    run_step([python, "scripts/build_index.py", "--reset", "--batch-size", str(args.batch_size)])
    print("\nKnowledge base update complete.")


if __name__ == "__main__":
    main()

