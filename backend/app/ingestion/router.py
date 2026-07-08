import logging

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.ingestion.pipeline import run_ingestion
from app.models import Project
from app.schemas import ProjectStatus

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post(
    "/{project_id}/ingest",
    status_code=status.HTTP_200_OK,
    summary="Trigger repository ingestion",
)
async def ingest_project(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Start ingestion synchronously. Returns when the pipeline finishes."""
    project = await _get_project_or_404(project_id, db)

    if project.status == "ingesting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingestion is already in progress for this project",
        )

    logger.info("Starting ingestion for project %d", project_id)
    await run_ingestion(project_id, db)
    return {"message": "Ingestion complete"}


@router.get(
    "/{project_id}/status",
    response_model=ProjectStatus,
    summary="Get ingestion status",
)
async def get_project_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> Project:
    return await _get_project_or_404(project_id, db)


async def _get_project_or_404(project_id: int, db: AsyncSession) -> Project:
    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Project {project_id} not found",
        )
    return project
