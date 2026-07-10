from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, field_validator


# ---------------------------------------------------------------------------
# Project schemas
# ---------------------------------------------------------------------------

class ProjectCreate(BaseModel):
    name: str
    source_type: str  # 'github' | 'zip'
    source_url: Optional[str] = None

    @field_validator("source_type")
    @classmethod
    def validate_source_type(cls, v: str) -> str:
        if v not in ("github", "zip"):
            raise ValueError("source_type must be 'github' or 'zip'")
        return v


class ProjectResponse(BaseModel):
    id: int
    name: str
    source_type: str
    source_url: Optional[str]
    status: str
    ingestion_progress: int
    current_stage_label: Optional[str]
    total_files: Optional[int]
    total_chunks: Optional[int]
    language_breakdown: Optional[str]  # raw JSON string
    error_message: Optional[str]
    faiss_index_path: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class ProjectStatus(BaseModel):
    id: int
    status: str
    ingestion_progress: int
    current_stage_label: Optional[str]
    total_files: Optional[int]
    total_chunks: Optional[int]
    error_message: Optional[str]

    model_config = {"from_attributes": True}


# ---------------------------------------------------------------------------
# File tree schemas
# ---------------------------------------------------------------------------

class FileNode(BaseModel):
    path: str
    type: str  # 'file' | 'directory'
    language: Optional[str] = None
    line_count: Optional[int] = None
    chunk_count: Optional[int] = None
    children: Optional[list["FileNode"]] = None


FileNode.model_rebuild()


# ---------------------------------------------------------------------------
# Conversation / Message schemas
# ---------------------------------------------------------------------------

class ConversationResponse(BaseModel):
    id: int
    project_id: int
    title: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class MessageResponse(BaseModel):
    id: int
    conversation_id: int
    role: str
    content: str
    citations: Optional[str]  # raw JSON string
    model_used: Optional[str]
    created_at: str

    model_config = {"from_attributes": True}


class ChatRequest(BaseModel):
    message: str
    conversation_id: Optional[int] = None


# ---------------------------------------------------------------------------
# Search / chunk schemas
# ---------------------------------------------------------------------------

class ChunkResult(BaseModel):
    chunk_id: int
    file_path: str
    chunk_type: str
    name: Optional[str]
    content: str
    line_start: Optional[int]
    line_end: Optional[int]
    score: float


# ---------------------------------------------------------------------------
# Language breakdown schema
# ---------------------------------------------------------------------------

class LanguageBreakdown(BaseModel):
    language: str
    percent: float
    file_count: int