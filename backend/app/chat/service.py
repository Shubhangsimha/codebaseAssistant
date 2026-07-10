from __future__ import annotations

import json
import logging
import re
from collections.abc import AsyncIterator
from datetime import datetime, timezone

from pathlib import Path

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.chat.llm_client import stream_response
from app.chat.prompt_builder import build_messages
from app.config import settings
from app.database import AsyncSessionLocal
from app.models import Conversation, Message, Project
from app.search.service import search

logger = logging.getLogger(__name__)

_CITATION_RE = re.compile(
    r"\[file:\s*([^\],]+?),\s*lines?:\s*(\d+)-(\d+)\]",
    re.IGNORECASE,
)


async def _get_or_create_conversation(
    project_id: int,
    conversation_id: int | None,
    first_message: str,
    db: AsyncSession,
) -> Conversation:
    if conversation_id is not None:
        result = await db.execute(
            select(Conversation).where(
                Conversation.id == conversation_id,
                Conversation.project_id == project_id,
            )
        )
        conv = result.scalar_one_or_none()
        if conv is None:
            raise ValueError(f"Conversation {conversation_id} not found for project {project_id}")
        return conv

    title = (first_message[:77].strip() + "...") if len(first_message) > 80 else first_message[:80].strip()
    conv = Conversation(project_id=project_id, title=title)
    db.add(conv)
    await db.flush()
    return conv


async def _load_history(conversation_id: int, db: AsyncSession) -> list[dict]:
    result = await db.execute(
        select(Message)
        .where(Message.conversation_id == conversation_id)
        .order_by(Message.id)
    )
    messages = result.scalars().all()
    return [{"role": m.role, "content": m.content} for m in messages]


async def chat_stream(
    project_id: int,
    question: str,
    conversation_id: int | None,
) -> AsyncIterator[str]:
    """
    Owns its own DB session so it is safe to use inside StreamingResponse.
    FastAPI's get_db dependency closes the session when the route function
    returns — before StreamingResponse consumes the generator — causing
    "database is locked" errors on SQLite.

    Yields SSE-formatted strings:
      data: {"type":"token","content":"..."}
      data: {"type":"citations","citations":[...]}
      data: {"type":"done","conversation_id":N,"message_id":N}
      data: {"type":"error","message":"..."}
    """
    async with AsyncSessionLocal() as db:
        try:
            # Verify project exists and is ready
            proj_result = await db.execute(select(Project).where(Project.id == project_id))
            project = proj_result.scalar_one_or_none()
            if project is None:
                yield _sse({"type": "error", "message": f"Project {project_id} not found"})
                return
            if project.status != "ready":
                yield _sse({"type": "error", "message": "Project is not ready yet"})
                return

            # Guard: FAISS index must exist
            faiss_path = Path(settings.data_dir) / "faiss" / f"{project_id}.faiss"
            if not faiss_path.exists():
                yield _sse({"type": "error", "message": "Search index not found. Try re-ingesting the project."})
                return

            conv = await _get_or_create_conversation(project_id, conversation_id, question, db)
            await db.flush()

            # Persist user message
            user_msg = Message(conversation_id=conv.id, role="user", content=question)
            db.add(user_msg)
            await db.flush()

            # Load history before the new user message
            history = await _load_history(conv.id, db)
            if history and history[-1]["role"] == "user":
                history = history[:-1]

            # Retrieve relevant chunks
            chunks = await search(question, project_id, db, top_k=8)

            messages = build_messages(question, chunks, history)

            # Stream LLM response
            full_response: list[str] = []
            model_used: str = "unknown"
            async for token, model in stream_response(messages):
                full_response.append(token)
                model_used = model
                yield _sse({"type": "token", "content": token})

            response_text = "".join(full_response)

            citations = _extract_citations(response_text, chunks)
            if citations:
                yield _sse({"type": "citations", "citations": citations})

            assistant_msg = Message(
                conversation_id=conv.id,
                role="assistant",
                content=response_text,
                citations=json.dumps(citations) if citations else None,
                model_used=model_used,
            )
            db.add(assistant_msg)
            await db.flush()
            await db.commit()

            yield _sse({
                "type": "done",
                "conversation_id": conv.id,
                "message_id": assistant_msg.id,
            })

        except Exception:
            logger.exception("chat_stream error for project %d", project_id)
            yield _sse({"type": "error", "message": "An error occurred. Please try again."})


def _sse(payload: dict) -> str:
    return f"data: {json.dumps(payload)}\n\n"


def _extract_citations(text: str, chunks: list[dict]) -> list[dict]:
    """
    Parse [file: path, lines: N-M] markers from the LLM response.
    Fall back to attaching the top-3 retrieved chunks if none are found.
    """
    found = []
    for m in _CITATION_RE.finditer(text):
        found.append({
            "file": m.group(1).strip(),
            "line_start": int(m.group(2)),
            "line_end": int(m.group(3)),
        })

    if found:
        # Deduplicate
        seen: set[tuple] = set()
        unique = []
        for c in found:
            key = (c["file"], c["line_start"], c["line_end"])
            if key not in seen:
                seen.add(key)
                unique.append(c)
        return unique

    # If the LLM didn't emit citations in the expected format, use top chunks
    fallback = []
    for chunk in chunks[:3]:
        if chunk.get("file_path") and chunk.get("line_start") is not None:
            fallback.append({
                "file": chunk["file_path"],
                "line_start": chunk["line_start"],
                "line_end": chunk["line_end"] or chunk["line_start"],
            })
    return fallback
