# mia/embedder.py
from __future__ import annotations

import numpy as np
import torch
from sentence_transformers import SentenceTransformer


class Embedder:
    """Lazy-load wrapper around SentenceTransformer."""

    def __init__(self, model_name: str = "BAAI/bge-m3", device: str = "auto"):
        self.model_name = model_name
        self._device = device
        self._model: SentenceTransformer | None = None

    @property
    def model(self) -> SentenceTransformer:
        if self._model is None:
            device = self._device
            if device == "auto":
                device = "cuda" if torch.cuda.is_available() else "cpu"
            self._model = SentenceTransformer(self.model_name, device=device)
        return self._model

    def encode_query(self, queries: list[str]) -> np.ndarray:
        m = self.model
        if hasattr(m, "encode_query"):
            emb = m.encode_query(
                queries,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        else:
            emb = m.encode(
                queries,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        return np.asarray(emb, dtype="float32")

    def encode_documents(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        m = self.model
        if hasattr(m, "encode_document"):
            emb = m.encode_document(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        else:
            emb = m.encode(
                texts,
                batch_size=batch_size,
                show_progress_bar=True,
                normalize_embeddings=True,
                convert_to_numpy=True,
            )
        return np.asarray(emb, dtype="float32")

    def encode(self, texts: list[str], batch_size: int = 32) -> np.ndarray:
        """Generic encode, no query/document distinction."""
        emb = self.model.encode(
            texts,
            batch_size=batch_size,
            show_progress_bar=True,
            normalize_embeddings=True,
            convert_to_numpy=True,
        )
        return np.asarray(emb, dtype="float32")

    @property
    def dim(self) -> int:
        return self.model.get_sentence_embedding_dimension()
