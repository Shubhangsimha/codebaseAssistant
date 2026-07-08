"""Ingestion pipeline — all 5 stages.

Stage 1: Acquire (clone / extract ZIP)
Stage 2: Walk files + persist ProjectFile records
Stage 3: Parse source code into CodeUnits
Stage 4: Chunk + embed all CodeUnits
Stage 5: Build FAISS index + persist ProjectChunk records
"""
from __future__ import annotations

import json
import logging
import tempfile
from pathlib import Path

import numpy as np
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.ingestion.ast_parser import parse_file
from app.ingestion.chunker import Chunk, chunk_code_unit
from app.ingestion.embedder import Embedder, FAISSStore
from app.ingestion.file_walker import walk_files
from app.ingestion.git_ingestion import clone_repository
from app.ingestion.zip_ingestion import extract_zip
from app.models import Project, ProjectChunk, ProjectFile

logger = logging.getLogger(__name__)


async def run_ingestion(project_id: int, db: AsyncSession) -> None:
    project = await _load_project(project_id, db)
    if project is None:
        logger.error("run_ingestion: project %d not found", project_id)
        return

    try:
        file_entries = await _stage_acquire(project, db)
        file_records = await _stage_walk_and_persist(project, db, file_entries)
        all_chunks = await _stage_parse_and_chunk(project, db, file_entries, file_records)
        await _stage_embed_and_index(project, db, all_chunks, file_records)
    except Exception as exc:
        logger.exception("Ingestion failed for project %d", project_id)
        project.status = "failed"
        project.error_message = str(exc)
        await db.flush()


# ---------------------------------------------------------------------------
# Stage 1: Acquire source code
# ---------------------------------------------------------------------------

async def _stage_acquire(project: Project, db: AsyncSession) -> list[dict]:
    project.status = "ingesting"
    project.ingestion_progress = 0
    project.current_stage_label = "Cloning repository..."
    await db.flush()

    tmp_dir = Path(tempfile.mkdtemp(prefix="codesage_"))

    if project.source_type == "github":
        if not project.source_url:
            raise ValueError("GitHub project has no source_url set")
        repo_root = clone_repository(project.source_url, tmp_dir)
    elif project.source_type == "zip":
        if not project.source_url:
            raise ValueError("ZIP project has no source_url (upload path) set")
        repo_root = extract_zip(Path(project.source_url), tmp_dir)
    else:
        raise ValueError(f"Unknown source_type: {project.source_type!r}")

    project.repo_path = str(repo_root)
    project.ingestion_progress = 10
    project.current_stage_label = "Scanning files..."
    await db.flush()
    logger.info("Acquired source for project %d at %s", project.id, repo_root)

    return walk_files(repo_root)


# ---------------------------------------------------------------------------
# Stage 2: Walk + persist ProjectFile records
# ---------------------------------------------------------------------------

async def _stage_walk_and_persist(
    project: Project,
    db: AsyncSession,
    file_entries: list[dict],
) -> dict[str, ProjectFile]:
    if not file_entries:
        raise ValueError(
            "No source files found in the repository. "
            "The repo may be empty or contain only unsupported file types."
        )

    lang_counts: dict[str, int] = {}
    for entry in file_entries:
        lang_counts[entry["language"]] = lang_counts.get(entry["language"], 0) + 1

    total = len(file_entries)
    breakdown = {lang: round(count / total * 100, 1) for lang, count in lang_counts.items()}
    project.language_breakdown = json.dumps(breakdown)
    project.total_files = total
    project.ingestion_progress = 20
    project.current_stage_label = "Parsing source code..."
    await db.flush()

    file_records: dict[str, ProjectFile] = {}
    for entry in file_entries:
        line_count = _count_lines(entry["path"])
        file_record = ProjectFile(
            project_id=project.id,
            file_path=entry["relative_path"],
            language=entry["language"],
            line_count=line_count,
            chunk_count=0,
        )
        db.add(file_record)
        await db.flush()  # get the id
        file_records[entry["relative_path"]] = file_record

    logger.info("Persisted %d file records for project %d", total, project.id)
    return file_records


# ---------------------------------------------------------------------------
# Stage 3: Parse source code + chunk
# ---------------------------------------------------------------------------

async def _stage_parse_and_chunk(
    project: Project,
    db: AsyncSession,
    file_entries: list[dict],
    file_records: dict[str, ProjectFile],
) -> list[tuple[Chunk, int]]:
    """Returns list of (Chunk, file_id)."""
    all_chunks: list[tuple[Chunk, int]] = []

    for entry in file_entries:
        try:
            raw = Path(entry["path"]).read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

        units = parse_file(entry["relative_path"], raw)
        file_record = file_records.get(entry["relative_path"])
        if file_record is None:
            continue

        file_chunks: list[Chunk] = []
        for unit in units:
            file_chunks.extend(chunk_code_unit(unit))

        file_record.chunk_count = len(file_chunks)
        all_chunks.extend((c, file_record.id) for c in file_chunks)

    project.ingestion_progress = 50
    project.current_stage_label = "Generating embeddings..."
    await db.flush()
    logger.info("Parsed %d total chunks for project %d", len(all_chunks), project.id)
    return all_chunks


# ---------------------------------------------------------------------------
# Stage 4+5: Embed + build FAISS index + persist ProjectChunk records
# ---------------------------------------------------------------------------

async def _stage_embed_and_index(
    project: Project,
    db: AsyncSession,
    all_chunks: list[tuple[Chunk, int]],
    file_records: dict[str, ProjectFile],
) -> None:
    if not all_chunks:
        project.status = "ready"
        project.ingestion_progress = 100
        project.current_stage_label = "Complete"
        await db.flush()
        return

    texts = [c.content for c, _ in all_chunks]
    embedder = Embedder()
    embeddings: np.ndarray = embedder.embed_batch(texts)

    project.ingestion_progress = 80
    project.current_stage_label = "Saving to search index..."
    await db.flush()

    # Persist ProjectChunk rows first (need DB ids for the FAISS meta map)
    chunk_db_ids: list[int] = []
    for faiss_pos, (chunk, file_id) in enumerate(all_chunks):
        db_chunk = ProjectChunk(
            project_id=project.id,
            file_id=file_id,
            faiss_index=faiss_pos,
            chunk_type=chunk.chunk_type.value,
            name=chunk.name,
            content=chunk.content,
            line_start=chunk.line_start,
            line_end=chunk.line_end,
            token_count=None,
        )
        db.add(db_chunk)
        await db.flush()
        chunk_db_ids.append(db_chunk.id)

    data_dir = Path(settings.data_dir)
    store = FAISSStore(project.id, data_dir)
    store.create_index(embeddings, chunk_db_ids)

    project.total_chunks = len(all_chunks)
    project.faiss_index_path = str(store.index_path)
    project.status = "ready"
    project.ingestion_progress = 100
    project.current_stage_label = "Complete"
    await db.flush()

    logger.info(
        "Ingestion complete for project %d: %d files, %d chunks",
        project.id, project.total_files, len(all_chunks),
    )


# ---------------------------------------------------------------------------
# Utilities
# ---------------------------------------------------------------------------

async def _load_project(project_id: int, db: AsyncSession) -> Project | None:
    result = await db.execute(select(Project).where(Project.id == project_id))
    return result.scalar_one_or_none()


def _count_lines(path: Path) -> int:
    try:
        return sum(1 for _ in path.open("rb"))
    except OSError:
        return 0
