from __future__ import annotations

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.config import settings
from app.ingestion.embedder import Embedder, FAISSIndex
from app.models import ProjectChunk

_embedder: Embedder | None = None


def _get_embedder() -> Embedder:
    global _embedder
    if _embedder is None:
        _embedder = Embedder()
    return _embedder


async def search(
    query: str,
    project_id: int,
    db: AsyncSession,
    top_k: int = 8,
) -> list[dict]:
    embedder = _get_embedder()
    query_vec = embedder.embed_batch([query])

    data_dir = Path(settings.data_dir)
    store = FAISSIndex.load_for_project(project_id, data_dir)
    distances, chunk_ids = store.search(query_vec[0], top_k)

    if not chunk_ids:
        return []

    result = await db.execute(
        select(ProjectChunk)
        .options(selectinload(ProjectChunk.file))
        .where(ProjectChunk.id.in_(chunk_ids))
    )
    chunks_by_id = {c.id: c for c in result.scalars().all()}

    id_to_rank = {cid: i for i, cid in enumerate(chunk_ids)}
    results = []
    for cid, dist in zip(chunk_ids, distances):
        chunk = chunks_by_id.get(cid)
        if chunk is None:
            continue
        file_path = chunk.file.file_path if chunk.file else ""
        results.append({
            "chunk_id": chunk.id,
            "file_path": file_path,
            "chunk_type": chunk.chunk_type,
            "name": chunk.name,
            "content": chunk.content,
            "line_start": chunk.line_start,
            "line_end": chunk.line_end,
            "score": float(dist),
        })

    results.sort(key=lambda r: id_to_rank.get(r["chunk_id"], 999))
    return results
