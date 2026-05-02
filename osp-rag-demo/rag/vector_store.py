from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional


def _clean_metadata(metadata: Dict[str, Any]) -> Dict[str, Any]:
    cleaned: Dict[str, Any] = {}
    for key, value in metadata.items():
        if value is None:
            cleaned[key] = ""
        elif isinstance(value, (str, int, float, bool)):
            cleaned[key] = value
        else:
            cleaned[key] = json.dumps(value, ensure_ascii=False)
    return cleaned


@dataclass
class VectorSearchResult:
    id: str
    text: str
    metadata: dict
    distance: float
    score: float


class ChromaVectorStore:
    def __init__(self, persist_dir: str | Path, collection_name: str):
        try:
            import chromadb
            from chromadb.config import Settings
        except ImportError as exc:
            raise ImportError(
                "chromadb is required. Install dependencies with "
                "`python -m pip install -r requirements.txt`."
            ) from exc

        self.persist_dir = Path(persist_dir)
        self.persist_dir.mkdir(parents=True, exist_ok=True)
        self.collection_name = collection_name
        self.client = chromadb.PersistentClient(
            path=str(self.persist_dir),
            settings=Settings(anonymized_telemetry=False),
        )
        self.collection = self.client.get_or_create_collection(
            name=collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def reset(self) -> None:
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": "cosine"},
        )

    def count(self) -> int:
        return int(self.collection.count())

    def upsert(
        self,
        *,
        ids: List[str],
        texts: List[str],
        metadatas: List[dict],
        embeddings: List[List[float]],
        batch_size: int = 128,
    ) -> None:
        for start in range(0, len(ids), batch_size):
            end = start + batch_size
            self.collection.upsert(
                ids=ids[start:end],
                documents=texts[start:end],
                metadatas=[_clean_metadata(m) for m in metadatas[start:end]],
                embeddings=embeddings[start:end],
            )

    def query(
        self,
        *,
        query_embedding: List[float],
        top_k: int = 8,
        where: Optional[dict] = None,
    ) -> List[VectorSearchResult]:
        result = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=top_k,
            where=where,
            include=["documents", "metadatas", "distances"],
        )
        ids = result.get("ids", [[]])[0]
        documents = result.get("documents", [[]])[0]
        metadatas = result.get("metadatas", [[]])[0]
        distances = result.get("distances", [[]])[0]

        rows: List[VectorSearchResult] = []
        for item_id, document, metadata, distance in zip(ids, documents, metadatas, distances):
            distance_value = float(distance)
            score = max(0.0, min(1.0, 1.0 - distance_value))
            rows.append(
                VectorSearchResult(
                    id=item_id,
                    text=document or "",
                    metadata=metadata or {},
                    distance=distance_value,
                    score=score,
                )
            )
        return rows

