"""Ingestion pipeline.

Milestone 1: stages 1 (acquire) + 2 (file walk + persist file metadata).
Milestone 2 will add stages 3-5 (parse, embed, store vectors).
"""
import logging
import tempfile
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.ingestion.file_walker import walk_files
from app.ingestion.git_ingestion import clone_repository
from app.ingestion.zip_ingestion import extract_zip
from app.models import Project, ProjectFile

logger = logging.getLogger(__name__)


async def run_ingestion(project_id: int, db: AsyncSession) -> None:
    """Run the full ingestion pipeline for a project.

    Updates project.status throughout so the frontend can poll progress.
    On any unrecoverable error the status is set to 'failed' with a message.
    """
    project = await _load_project(project_id, db)
    if project is None:
        logger.error("run_ingestion: project %d not found", project_id)
        return

    try:
        await _stage_acquire(project, db)
        await _stage_walk_and_persist(project, db)
    except Exception as exc:
        logger.exception("Ingestion failed for project %d", project_id)
        project.status = "failed"
        project.error_message = str(exc)
        await db.flush()


# ---------------------------------------------------------------------------
# Stage helpers
# ---------------------------------------------------------------------------

async def _stage_acquire(project: Project, db: AsyncSession) -> None:
    """Clone / extract source code to a temp directory."""
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
    project.ingestion_progress = 20
    project.current_stage_label = "Scanning files..."
    await db.flush()
    logger.info("Acquired source for project %d at %s", project.id, repo_root)


async def _stage_walk_and_persist(project: Project, db: AsyncSession) -> None:
    """Walk the repository, persist file records, mark project ready."""
    if not project.repo_path:
        raise RuntimeError("repo_path is not set — acquire stage must run first")

    repo_root = Path(project.repo_path)
    file_entries = walk_files(repo_root)

    if not file_entries:
        raise ValueError(
            "No source files found in the repository. "
            "The repo may be empty or contain only unsupported file types."
        )

    # Compute language breakdown
    lang_counts: dict[str, int] = {}
    for entry in file_entries:
        lang_counts[entry["language"]] = lang_counts.get(entry["language"], 0) + 1

    total = len(file_entries)
    import json
    breakdown = {lang: round(count / total * 100, 1) for lang, count in lang_counts.items()}
    project.language_breakdown = json.dumps(breakdown)

    # Persist one ProjectFile row per discovered file
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

    project.total_files = total
    project.ingestion_progress = 40
    project.current_stage_label = "Parsing source code..."
    await db.flush()

    # Milestone 1: mark ready here (stages 3-5 added in Milestone 2)
    project.status = "ready"
    project.ingestion_progress = 100
    project.current_stage_label = "Complete"
    await db.flush()
    logger.info(
        "Ingestion complete for project %d: %d files", project.id, total
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
