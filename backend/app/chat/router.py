from __future__ import annotations

import logging

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.service import chat_stream
from app.database import get_db
from app.models import Conversation, Message
from app.schemas import ChatRequest, ConversationResponse, MessageResponse

logger = logging.getLogger(__name__)
router = APIRouter()


@router.post("/{project_id}/chat")
async def post_chat(
    project_id: int,
    body: ChatRequest,
) -> StreamingResponse:
    """Stream a chat response as Server-Sent Events."""
    return StreamingResponse(
        chat_stream(project_id, body.message, body.conversation_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "X-Accel-Buffering": "no",
        },
    )


@router.get("/{project_id}/conversations", response_model=list[ConversationResponse])
async def list_conversations(
    project_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[Conversation]:
    result = await db.execute(
        select(Conversation)
        .where(Conversation.project_id == project_id)
        .order_by(Conversation.created_at.desc())
    )
    return list(result.scalars().all())


@router.get(
    "/{project_id}/conversations/{conversation_id}/messages",
    response_model=list[MessageResponse],
)
async def get_messages(
    project_id: int,
    conversation_id: int,
    db: AsyncSession = Depends(get_db),
) -> list[Message]:
    # Verify conversation belongs to this project
    conv_result = await db.execute(
        select(Conversation).where(
            Conversation.id == conversation_id,
            Conversation.project_id == project_id,
        )
    )
    if conv_result.scalar_one_or_none() is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Conversation {conversation_id} not found for project {project_id}",
        )

    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    return list(result.scalars().all())
