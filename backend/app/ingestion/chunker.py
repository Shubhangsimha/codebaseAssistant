from __future__ import annotations

from dataclasses import dataclass

from langchain_text_splitters import RecursiveCharacterTextSplitter

from app.ingestion.ast_parser import ChunkType, CodeUnit
from app.ingestion.token_counter import count_tokens

MAX_TOKENS = 512
OVERLAP_TOKENS = 64


@dataclass
class Chunk:
    file_path: str
    language: str
    chunk_type: ChunkType
    name: str | None
    parent_name: str | None
    content: str
    line_start: int
    line_end: int
    sub_index: int | None
    sub_total: int | None


def chunk_code_unit(unit: CodeUnit) -> list[Chunk]:
    token_count = count_tokens(unit.content)

    if token_count <= MAX_TOKENS:
        return [Chunk(
            file_path=unit.file_path,
            language=unit.language,
            chunk_type=unit.chunk_type,
            name=unit.name,
            parent_name=unit.parent_name,
            content=unit.content,
            line_start=unit.line_start,
            line_end=unit.line_end,
            sub_index=None,
            sub_total=None,
        )]

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=MAX_TOKENS,
        chunk_overlap=OVERLAP_TOKENS,
        length_function=count_tokens,
        separators=["\n\n", "\n", " ", ""],
    )
    parts = splitter.split_text(unit.content)
    n = len(parts)
    chunks = []
    for i, part in enumerate(parts):
        prefix = (
            f"# File: {unit.file_path}, "
            f"{unit.chunk_type.value} '{unit.name}', "
            f"Lines: {unit.line_start}-{unit.line_end} "
            f"(part {i + 1} of {n})\n"
        )
        chunks.append(Chunk(
            file_path=unit.file_path,
            language=unit.language,
            chunk_type=unit.chunk_type,
            name=unit.name,
            parent_name=unit.parent_name,
            content=prefix + part,
            line_start=unit.line_start,
            line_end=unit.line_end,
            sub_index=i,
            sub_total=n,
        ))
    return chunks
