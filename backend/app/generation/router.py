from __future__ import annotations

import json
import logging

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.database import AsyncSessionLocal, get_db
from app.generation.api_scanner import scan_api_endpoints
from app.generation.architecture import generate_architecture
from app.generation.doc_generator import stream_docstring

logger = logging.getLogger(__name__)
router = APIRouter()


@router.get("/{project_id}/architecture")
async def get_architecture(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> dict:
    try:
        return await generate_architecture(project_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("Architecture generation failed for project %d", project_id)
        raise HTTPException(status_code=500, detail="Architecture generation failed")


@router.get("/{project_id}/api-endpoints")
async def get_api_endpoints(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[dict]:
    try:
        return await scan_api_endpoints(project_id, db)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    except Exception:
        logger.exception("API scan failed for project %d", project_id)
        raise HTTPException(status_code=500, detail="API endpoint scan failed")


@router.get("/{project_id}/chunks/{chunk_id}/docstring")
async def generate_docstring(
    project_id: int,
    chunk_id: int,
) -> StreamingResponse:
    """Stream a generated docstring for the given chunk as SSE."""
    async def _generate():
        async with AsyncSessionLocal() as db:
            try:
                async for token in stream_docstring(project_id, chunk_id, db):
                    payload = json.dumps({"type": "token", "content": token})
                    yield f"data: {payload}\n\n"
                yield 'data: {"type":"done"}\n\n'
            except Exception:
                logger.exception("Docstring generation failed for chunk %d", chunk_id)
                yield 'data: {"type":"error","message":"Docstring generation failed"}\n\n'

    return StreamingResponse(
        _generate(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )
