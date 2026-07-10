from __future__ import annotations

import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.graph.builder import build_dependency_graph
from app.graph.cycle_detector import find_cycles, nodes_in_cycles
from app.models import Project, ProjectFile

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{project_id}/graph")
async def get_dependency_graph(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != "ready":
        raise HTTPException(status_code=400, detail="Project is not ready")
    if not project.repo_path:
        raise HTTPException(status_code=400, detail="Repository path not available")

    repo_root = Path(project.repo_path)

    # Load all file records
    files_result = await db.execute(
        select(ProjectFile).where(ProjectFile.project_id == project_id)
    )
    files = files_result.scalars().all()

    # Read file contents (only code files, skip large ones)
    file_contents: dict[str, str] = {}
    for f in files:
        full_path = repo_root / f.file_path
        if not full_path.exists():
            continue
        try:
            size = full_path.stat().st_size
            if size > 100_000:
                continue
            file_contents[f.file_path] = full_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue

    if not file_contents:
        return {"nodes": [], "edges": [], "cycles": []}

    # Build graph
    adjacency = build_dependency_graph(file_contents)

    # Only keep nodes that have at least one edge (cleaner graph)
    active_files = set()
    for src, deps in adjacency.items():
        if deps:
            active_files.add(src)
            active_files.update(deps)

    # Detect cycles
    subgraph = {k: v for k, v in adjacency.items() if k in active_files}
    cycles = find_cycles(subgraph)
    cycle_nodes = nodes_in_cycles(cycles)

    # Build React Flow nodes + edges
    nodes = []
    edges = []
    edge_id = 0

    # Language lookup
    lang_map = {f.file_path: f.language for f in files}

    for file_path in active_files:
        nodes.append({
            "id": file_path,
            "data": {
                "label": file_path.split("/")[-1],
                "path": file_path,
                "language": lang_map.get(file_path),
                "cyclic": file_path in cycle_nodes,
            },
            "position": {"x": 0, "y": 0},  # layout handled client-side
            "type": "default",
        })

    for src, deps in subgraph.items():
        for dep in deps:
            if dep in active_files:
                cyclic_edge = src in cycle_nodes and dep in cycle_nodes
                edges.append({
                    "id": f"e{edge_id}",
                    "source": src,
                    "target": dep,
                    "data": {"cyclic": cyclic_edge},
                    "style": {"stroke": "#ef4444"} if cyclic_edge else {},
                })
                edge_id += 1

    return {
        "nodes": nodes,
        "edges": edges,
        "cycles": cycles,
    }
