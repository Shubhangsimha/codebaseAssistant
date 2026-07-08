from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import get_db
from app.models import Project
from app.search import service as search_service

router = APIRouter()


@router.get("/{project_id}/search")
async def search_chunks(
    project_id: int,
    q: str = Query(default=""),
    top_k: int = Query(default=8, ge=1, le=50),
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    if not q.strip():
        raise HTTPException(status_code=400, detail="Query parameter 'q' must not be empty")

    result = await db.execute(select(Project).where(Project.id == project_id))
    project = result.scalar_one_or_none()
    if project is None:
        raise HTTPException(status_code=404, detail="Project not found")
    if project.status != "ready":
        raise HTTPException(status_code=400, detail="Project is not ready for search")

    return await search_service.search(q, project_id, db, top_k=top_k)
