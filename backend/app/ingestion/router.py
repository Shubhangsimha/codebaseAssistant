import logging

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.common import get_project_or_404
from app.database import AsyncSessionLocal, get_db
from app.ingestion.pipeline import run_ingestion
from app.models import Project
from app.schemas import ProjectStatus

logger = logging.getLogger(__name__)
router = APIRouter()


async def _run_ingestion_background(project_id: int) -> None:
    """Run the ingestion pipeline in its own DB session (BackgroundTasks context)."""
    async with AsyncSessionLocal() as db:
        try:
            await run_ingestion(project_id, db)
            await db.commit()
        except Exception:
            await db.rollback()
            logger.exception("Background ingestion failed for project %d", project_id)


@router.post(
    "/{project_id}/ingest",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger repository ingestion",
)
async def ingest_project(
    project_id: int,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(get_db),
) -> dict[str, str]:
    """Enqueue ingestion as a background task. Returns 202 immediately."""
    project = await get_project_or_404(project_id, db)

    if project.status == "ingesting":
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail="Ingestion is already in progress for this project",
        )

    logger.info("Queuing background ingestion for project %d", project_id)
    background_tasks.add_task(_run_ingestion_background, project_id)
    return {"message": "Ingestion started"}


@router.get(
    "/{project_id}/status",
    response_model=ProjectStatus,
    summary="Get ingestion status",
)
async def get_project_status(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> Project:
    return await get_project_or_404(project_id, db)
