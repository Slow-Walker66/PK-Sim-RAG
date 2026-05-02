from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Iterable, List, Optional

from tqdm import tqdm

PROJECT_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_DIR))

from config import settings
from rag.github_client import GitHubDiscussionClient


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


def discussion_key(row: dict) -> str:
    return str(row.get("id") or row.get("number") or row.get("url"))


def merge_discussions(existing: List[dict], fresh: List[dict]) -> List[dict]:
    merged = {discussion_key(row): row for row in existing if discussion_key(row)}
    for row in fresh:
        key = discussion_key(row)
        if key:
            merged[key] = row
    return sorted(
        merged.values(),
        key=lambda row: row.get("updated_at") or row.get("created_at") or "",
        reverse=True,
    )


def latest_updated_at(rows: List[dict]) -> Optional[str]:
    values = [row.get("updated_at") for row in rows if row.get("updated_at")]
    return max(values) if values else None


def main() -> None:
    parser = argparse.ArgumentParser(description="Fetch GitHub Discussions via GraphQL API.")
    parser.add_argument("--owner", default=settings.github_owner)
    parser.add_argument("--repo", default=settings.github_repo)
    parser.add_argument(
        "--output",
        default=str(PROJECT_DIR / "data/processed/github_discussions.jsonl"),
        help="Output JSONL file.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        help="Max discussions to fetch. Omit this option to fetch all discussions.",
    )
    parser.add_argument(
        "--all",
        action="store_true",
        help="Fetch all discussions. This is the default when --limit is omitted.",
    )
    parser.add_argument(
        "--since-existing",
        action="store_true",
        help="Fetch only discussions updated after the newest local record, then merge.",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="Replace the output file instead of merging with existing local data.",
    )
    parser.add_argument("--page-size", type=int, default=25)
    parser.add_argument("--comments-first", type=int, default=100)
    args = parser.parse_args()

    if not settings.github_token:
        raise SystemExit("GITHUB_TOKEN is missing. Add it to .env before running this script.")

    client = GitHubDiscussionClient(settings.github_token, args.owner, args.repo)
    output = Path(args.output)
    output.parent.mkdir(parents=True, exist_ok=True)

    existing = [] if args.replace else read_jsonl(output)
    existing_keys = {discussion_key(row) for row in existing}
    cutoff = latest_updated_at(existing) if args.since_existing else None
    limit = None if args.all else args.limit

    fresh = []
    discussions = client.fetch_discussions(
        limit=limit,
        page_size=args.page_size,
        comments_first=args.comments_first,
    )
    progress_total = limit
    for discussion in tqdm(discussions, total=progress_total, desc="Fetching discussions"):
        if cutoff and discussion.get("updated_at") and discussion["updated_at"] <= cutoff:
            if discussion_key(discussion) in existing_keys:
                break
        fresh.append(discussion)

    rows = fresh if args.replace else merge_discussions(existing, fresh)
    write_jsonl(output, rows)
    print(
        f"Fetched {len(fresh)} discussions; local store has {len(rows)} discussions -> {output}"
    )


if __name__ == "__main__":
    main()
