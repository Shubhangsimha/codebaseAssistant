from __future__ import annotations

import json
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project, ProjectFile
from app.schemas import FileNode, LanguageBreakdown

router = APIRouter()


# ---------------------------------------------------------------------------
# GET /projects/:id/files  — nested file tree
# ---------------------------------------------------------------------------

@router.get("/{project_id}/files", response_model=dict)
async def get_file_tree(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    project = await _get_ready_project(project_id, db)

    result = await db.execute(
        select(ProjectFile)
        .where(ProjectFile.project_id == project_id)
        .order_by(ProjectFile.file_path)
    )
    files = result.scalars().all()

    tree = _build_tree(files)
    return {"tree": tree}


# ---------------------------------------------------------------------------
# GET /projects/:id/files/content?path=...  — raw file content
# ---------------------------------------------------------------------------

@router.get("/{project_id}/files/content")
async def get_file_content(
    project_id: int,
    path: str = Query(..., description="Relative file path from repo root"),
    db: AsyncSession = Depends(get_db),
) -> dict:
    project = await _get_ready_project(project_id, db)

    if not project.repo_path:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Repository path not available for this project",
        )

    repo_root = Path(project.repo_path)
    # Sanitize: strip leading slashes, resolve to prevent path traversal
    clean = path.lstrip("/").lstrip("\\")
    full_path = (repo_root / clean).resolve()

    # Ensure the resolved path is still inside the repo root
    try:
        full_path.relative_to(repo_root.resolve())
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid file path")

    if not full_path.exists() or not full_path.is_file():
        raise HTTPException(status_code=404, detail=f"File not found: {path}")

    try:
        content = full_path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        raise HTTPException(status_code=500, detail="Could not read file")

    # Determine language from DB record
    result = await db.execute(
        select(ProjectFile).where(
            ProjectFile.project_id == project_id,
            ProjectFile.file_path == clean,
        )
    )
    file_record = result.scalar_one_or_none()
    language = file_record.language if file_record else _ext_to_language(full_path.suffix)
    line_count = content.count("\n") + 1

    return {"content": content, "language": language, "line_count": line_count}


# ---------------------------------------------------------------------------
# GET /projects/:id/languages  — language breakdown
# ---------------------------------------------------------------------------

@router.get("/{project_id}/languages", response_model=list[LanguageBreakdown])
async def get_language_breakdown(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    project = await _get_ready_project(project_id, db)

    if not project.language_breakdown:
        return []

    try:
        raw: dict[str, float] = json.loads(project.language_breakdown)
    except (json.JSONDecodeError, TypeError):
        return []

    # Also get file counts per language
    result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = result.scalars().all()
    counts: dict[str, int] = {}
    for f in files:
        lang = f.language or "Unknown"
        counts[lang] = counts.get(lang, 0) + 1

    return [
        {"language": lang, "percent": pct, "file_count": counts.get(lang, 0)}
        for lang, pct in sorted(raw.items(), key=lambda x: -x[1])
    ]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def _get_ready_project(project_id: int, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != "ready":
        raise HTTPException(status_code=400, detail="Project is not ready")
    return project


def _build_tree(files: list[ProjectFile]) -> list[dict]:
    """Convert flat file list into a nested tree structure."""
    root: dict[str, dict] = {}

    for f in files:
        parts = f.file_path.replace("\\", "/").split("/")
        node = root
        for part in parts[:-1]:
            if part not in node:
                node[part] = {"__meta__": {"type": "directory", "path": part, "children": {}}}
            node = node[part]["__meta__"]["children"]
        filename = parts[-1]
        node[filename] = {
            "__meta__": {
                "type": "file",
                "path": f.file_path,
                "language": f.language,
                "line_count": f.line_count,
                "chunk_count": f.chunk_count,
                "children": None,
            }
        }

    return _flatten_tree(root, "")


def _flatten_tree(node: dict, prefix: str) -> list[dict]:
    items = []
    for name, value in sorted(node.items()):
        meta = value["__meta__"]
        entry: dict = {
            "path": meta["path"],
            "type": meta["type"],
            "language": meta.get("language"),
            "line_count": meta.get("line_count"),
            "chunk_count": meta.get("chunk_count"),
        }
        if meta["type"] == "directory":
            entry["children"] = _flatten_tree(meta["children"], meta["path"])
        else:
            entry["children"] = None
        items.append(entry)
    return items


_EXT_LANG: dict[str, str] = {
    ".py": "Python", ".js": "JavaScript", ".jsx": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript", ".go": "Go",
    ".java": "Java", ".rs": "Rust", ".cpp": "C++", ".c": "C",
    ".cs": "C#", ".rb": "Ruby", ".php": "PHP",
    ".json": "JSON", ".yaml": "YAML", ".yml": "YAML",
    ".md": "Markdown", ".sql": "SQL", ".sh": "Shell",
}


def _ext_to_language(ext: str) -> str:
    return _EXT_LANG.get(ext.lower(), "Unknown")
