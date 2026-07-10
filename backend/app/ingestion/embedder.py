from __future__ import annotations

import json
from pathlib import Path

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer

_MODEL_NAME = "BAAI/bge-small-en-v1.5"
_DIMS = 384

_model: SentenceTransformer | None = None


def _get_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer(_MODEL_NAME)
    return _model


class Embedder:
    def __init__(self) -> None:
        self._model = _get_model()

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        return self._model.encode(
            texts,
            batch_size=64,
            normalize_embeddings=True,
            show_progress_bar=False,
        ).astype(np.float32)


class FAISSIndex:
    def __init__(self, project_id: int, data_dir: Path) -> None:
        self.project_id = project_id
        self._index_path = data_dir / "faiss" / f"{project_id}.faiss"
        self._meta_path = data_dir / "faiss" / f"{project_id}.meta.json"
        self._index: faiss.IndexFlatIP | None = None
        # mapping: faiss position (int) → chunk db id (int)
        self._meta: dict[int, int] = {}

    # ------------------------------------------------------------------
    # Build
    # ------------------------------------------------------------------

    def create_index(self, embeddings: np.ndarray, chunk_ids: list[int]) -> None:
        assert embeddings.shape[0] == len(chunk_ids), "embeddings/chunk_ids length mismatch"
        self._index = faiss.IndexFlatIP(_DIMS)
        self._index.add(embeddings)
        self._meta = {i: cid for i, cid in enumerate(chunk_ids)}
        self.save()

    # ------------------------------------------------------------------
    # Search
    # ------------------------------------------------------------------

    def search(self, query_vec: np.ndarray, top_k: int) -> tuple[np.ndarray, list[int]]:
        """Returns (distances, chunk_db_ids)."""
        if self._index is None:
            raise RuntimeError("Index not loaded — call load() first")
        vec = query_vec.reshape(1, _DIMS).astype(np.float32)
        distances, positions = self._index.search(vec, top_k)
        chunk_ids = [self._meta[int(p)] for p in positions[0] if int(p) != -1]
        dists = [float(d) for d, p in zip(distances[0], positions[0]) if int(p) != -1]
        return np.array(dists, dtype=np.float32), chunk_ids

    # ------------------------------------------------------------------
    # Persistence
    # ------------------------------------------------------------------

    def save(self) -> None:
        self._index_path.parent.mkdir(parents=True, exist_ok=True)
        faiss.write_index(self._index, str(self._index_path))
        self._meta_path.write_text(
            json.dumps({str(k): v for k, v in self._meta.items()})
        )

    def load(self) -> None:
        self._index = faiss.read_index(str(self._index_path))
        raw = json.loads(self._meta_path.read_text())
        self._meta = {int(k): v for k, v in raw.items()}

    @classmethod
    def load_for_project(cls, project_id: int, data_dir: Path) -> "FAISSIndex":
        store = cls(project_id, data_dir)
        store.load()
        return store

    @property
    def index_path(self) -> Path:
        return self._index_path

    @property
    def size(self) -> int:
        return self._index.ntotal if self._index else 0
