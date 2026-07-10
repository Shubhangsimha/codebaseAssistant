import logging
from pathlib import Path

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.common import get_project_or_404
from app.database import get_db
from app.models import Project
from app.schemas import ProjectCreate, ProjectResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("", response_model=list[ProjectResponse])
async def list_projects(db: AsyncSession = Depends(get_db)) -> list[Project]:
    result = await db.execute(
        select(Project).order_by(Project.created_at.desc())
    )
    return list(result.scalars().all())


@router.post("", response_model=ProjectResponse, status_code=status.HTTP_201_CREATED)
async def create_project(
    body: ProjectCreate,
    db: AsyncSession = Depends(get_db),
) -> Project:
    project = Project(
        name=body.name,
        source_type=body.source_type,
        source_url=body.source_url,
        status="pending",
    )
    db.add(project)
    await db.flush()  # assigns ID before commit
    await db.refresh(project)
    logger.info("Created project id=%d name=%r", project.id, project.name)
    return project


@router.delete("/{project_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> None:
    project = await get_project_or_404(project_id, db)

    # Remove FAISS index file if it exists
    if project.faiss_index_path:
        faiss_path = Path(project.faiss_index_path)
        meta_path = faiss_path.with_suffix(".meta.json")
        for p in (faiss_path, meta_path):
            if p.exists():
                p.unlink()
                logger.info("Deleted FAISS file: %s", p)

    await db.delete(project)
    logger.info("Deleted project id=%d", project_id)
