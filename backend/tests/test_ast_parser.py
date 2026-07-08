from app.ingestion.ast_parser import (
    ChunkType,
    CodeUnit,
    parse_file,
    parse_javascript,
    parse_python,
    _fallback,
)
from tests.conftest import JS_SAMPLE, PYTHON_SAMPLE


def test_python_returns_code_units():
    units = parse_python("test.py", PYTHON_SAMPLE)
    assert len(units) >= 4  # module + class + 2 methods + 2 functions


def test_python_standalone_functions():
    units = parse_python("test.py", PYTHON_SAMPLE)
    funcs = [u for u in units if u.chunk_type == ChunkType.FUNCTION]
    names = [u.name for u in funcs]
    assert "standalone_func" in names
    assert "another_func" in names


def test_python_methods_have_parent():
    units = parse_python("test.py", PYTHON_SAMPLE)
    methods = [u for u in units if u.chunk_type == ChunkType.METHOD]
    assert len(methods) >= 2
    for m in methods:
        assert m.parent_name == "MyClass"


def test_python_line_numbers():
    units = parse_python("test.py", PYTHON_SAMPLE)
    for u in units:
        assert u.line_start >= 1
        assert u.line_end >= u.line_start


def test_python_no_overlapping_ranges():
    units = parse_python("test.py", PYTHON_SAMPLE)
    # functions should not overlap each other
    funcs = sorted(
        [u for u in units if u.chunk_type == ChunkType.FUNCTION],
        key=lambda u: u.line_start,
    )
    for i in range(len(funcs) - 1):
        assert funcs[i].line_end <= funcs[i + 1].line_start + 1


def test_javascript_extracts_functions():
    units = parse_javascript("router.js", JS_SAMPLE, "javascript")
    func_names = [u.name for u in units if u.chunk_type in (ChunkType.FUNCTION, ChunkType.METHOD)]
    assert "handleAuth" in func_names


def test_javascript_extracts_class():
    units = parse_javascript("router.js", JS_SAMPLE, "javascript")
    classes = [u for u in units if u.chunk_type == ChunkType.CLASS]
    assert any(c.name == "UserController" for c in classes)


def test_fallback_produces_blocks():
    content = "\n".join(f"line {i}" for i in range(500))
    units = _fallback("big.txt", "text", content)
    assert len(units) >= 2
    for u in units:
        assert u.chunk_type == ChunkType.BLOCK


def test_parse_file_dispatches_python():
    units = parse_file("script.py", PYTHON_SAMPLE)
    types = {u.chunk_type for u in units}
    assert ChunkType.FUNCTION in types or ChunkType.METHOD in types


def test_parse_file_fallback_for_unknown_extension():
    units = parse_file("data.xyz", "hello world\n" * 10)
    assert len(units) >= 1
    assert all(u.chunk_type == ChunkType.BLOCK for u in units)


def test_parse_file_empty_content():
    units = parse_file("empty.py", "")
    assert len(units) >= 1


def test_parse_file_markdown():
    units = parse_file("README.md", "# Title\n\nSome content.\n")
    assert len(units) >= 1
