from __future__ import annotations

from functools import cached_property
from typing import Iterable, List


class EmbeddingModel:
    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "", batch_size: int = 16):
        self.model_name = model_name
        self.device = device or None
        self.batch_size = batch_size

    @cached_property
    def model(self):
        try:
            from sentence_transformers import SentenceTransformer
        except ImportError as exc:
            raise ImportError(
                "sentence-transformers is required. Install dependencies with "
                "`python -m pip install -r requirements.txt`."
            ) from exc
        return SentenceTransformer(self.model_name, device=self.device)

    def encode(self, texts: Iterable[str]) -> List[List[float]]:
        texts = list(texts)
        if not texts:
            return []
        vectors = self.model.encode(
            texts,
            batch_size=self.batch_size,
            normalize_embeddings=True,
            show_progress_bar=False,
            convert_to_numpy=True,
        )
        return vectors.astype("float32").tolist()

