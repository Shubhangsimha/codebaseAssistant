from app.ingestion.ast_parser import ChunkType, CodeUnit
from app.ingestion.chunker import chunk_code_unit
from app.ingestion.token_counter import count_tokens


def _make_unit(content: str, name: str = "my_func") -> CodeUnit:
    return CodeUnit(
        file_path="test.py",
        language="python",
        chunk_type=ChunkType.FUNCTION,
        name=name,
        content=content,
        line_start=1,
        line_end=content.count("\n") + 1,
    )


def test_short_unit_produces_one_chunk():
    unit = _make_unit("def foo():\n    return 1\n")
    chunks = chunk_code_unit(unit)
    assert len(chunks) == 1
    assert chunks[0].sub_index is None
    assert chunks[0].sub_total is None


def test_short_unit_no_prefix():
    unit = _make_unit("def foo():\n    return 1\n")
    chunks = chunk_code_unit(unit)
    assert "part 1 of" not in chunks[0].content


def test_long_unit_produces_multiple_chunks():
    # ~1200 tokens
    long_content = "x = 1\n" * 300
    unit = _make_unit(long_content)
    chunks = chunk_code_unit(unit)
    assert len(chunks) >= 2


def test_long_unit_chunks_under_max_tokens():
    long_content = "x = 1\n" * 300
    unit = _make_unit(long_content)
    chunks = chunk_code_unit(unit)
    for chunk in chunks:
        assert count_tokens(chunk.content) <= 600  # allow small overhead from prefix


def test_long_unit_prefix_contains_location():
    long_content = "x = 1\n" * 300
    unit = _make_unit(long_content, name="big_function")
    chunks = chunk_code_unit(unit)
    for i, chunk in enumerate(chunks):
        assert "big_function" in chunk.content
        assert f"part {i + 1} of" in chunk.content


def test_long_unit_sub_index():
    long_content = "x = 1\n" * 300
    unit = _make_unit(long_content)
    chunks = chunk_code_unit(unit)
    for i, chunk in enumerate(chunks):
        assert chunk.sub_index == i
        assert chunk.sub_total == len(chunks)


def test_chunk_preserves_metadata():
    unit = _make_unit("def bar():\n    pass\n", name="bar")
    unit.parent_name = "MyClass"
    chunks = chunk_code_unit(unit)
    assert chunks[0].parent_name == "MyClass"
    assert chunks[0].language == "python"
    assert chunks[0].file_path == "test.py"


def test_deterministic():
    content = "y = 2\n" * 200
    unit = _make_unit(content)
    chunks1 = chunk_code_unit(unit)
    chunks2 = chunk_code_unit(unit)
    assert [c.content for c in chunks1] == [c.content for c in chunks2]
