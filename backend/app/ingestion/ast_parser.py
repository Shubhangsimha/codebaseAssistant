"""AST-based code parser.

Implements M2-T02 through M2-T06:
  - CodeUnit dataclass + ChunkType enum (T02)
  - Python parser (T03)
  - JavaScript / TypeScript parser (T04)
  - Go + Java parsers (T05)
  - Fallback text chunker + parse_file dispatcher (T06)
  - Rust parser (T06)
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path

from tree_sitter import Language, Node, Parser

from app.ingestion.languages import (
    GO_LANGUAGE,
    JAVA_LANGUAGE,
    JS_LANGUAGE,
    PY_LANGUAGE,
    RUST_LANGUAGE,
    TS_LANGUAGE,
    TSX_LANGUAGE,
)

# ---------------------------------------------------------------------------
# M2-T02: shared contracts
# ---------------------------------------------------------------------------

class ChunkType(str, Enum):
    FUNCTION = "FUNCTION"
    CLASS = "CLASS"
    METHOD = "METHOD"
    MODULE = "MODULE"
    BLOCK = "BLOCK"


@dataclass
class CodeUnit:
    file_path: str
    language: str
    chunk_type: ChunkType
    name: str | None
    content: str
    line_start: int
    line_end: int
    parent_name: str | None = None
    extra: dict = field(default_factory=dict)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _node_text(node: Node, src: bytes) -> str:
    return src[node.start_byte:node.end_byte].decode("utf-8", errors="replace")


def _lines(node: Node) -> tuple[int, int]:
    # tree-sitter rows are 0-indexed; we expose 1-indexed
    return node.start_point[0] + 1, node.end_point[0] + 1


def _make_parser(language: Language) -> Parser:
    p = Parser(language)
    return p


# ---------------------------------------------------------------------------
# M2-T03: Python
# ---------------------------------------------------------------------------

def parse_python(file_path: str, content: str) -> list[CodeUnit]:
    src = content.encode("utf-8")
    parser = _make_parser(PY_LANGUAGE)
    tree = parser.parse(src)
    units: list[CodeUnit] = []

    # Module header: imports block (lines 1 .. first non-import/non-docstring)
    module_lines = _extract_module_header(tree.root_node, src)
    if module_lines:
        start, end, text = module_lines
        units.append(CodeUnit(
            file_path=file_path, language="python",
            chunk_type=ChunkType.MODULE, name="<module>",
            content=text, line_start=start, line_end=end,
        ))

    for node in tree.root_node.children:
        if node.type == "function_definition":
            name = _get_child_text(node, "identifier", src)
            units.append(CodeUnit(
                file_path=file_path, language="python",
                chunk_type=ChunkType.FUNCTION, name=name,
                content=_node_text(node, src),
                line_start=_lines(node)[0], line_end=_lines(node)[1],
            ))
        elif node.type == "class_definition":
            class_name = _get_child_text(node, "identifier", src)
            class_start, class_end = _lines(node)
            # Class declaration up to first method
            class_header = _extract_class_header(node, src)
            units.append(CodeUnit(
                file_path=file_path, language="python",
                chunk_type=ChunkType.CLASS, name=class_name,
                content=class_header,
                line_start=class_start, line_end=class_end,
            ))
            # Methods inside class
            for method in _find_methods_python(node, src):
                units.append(CodeUnit(
                    file_path=file_path, language="python",
                    chunk_type=ChunkType.METHOD, name=method["name"],
                    content=method["content"],
                    line_start=method["line_start"], line_end=method["line_end"],
                    parent_name=class_name,
                ))

    return units if units else _fallback(file_path, "python", content)


def _extract_module_header(root: Node, src: bytes) -> tuple[int, int, str] | None:
    """Return (start_line, end_line, text) for the import block."""
    import_lines: list[Node] = []
    for child in root.children:
        if child.type in ("import_statement", "import_from_statement",
                          "expression_statement", "comment"):
            import_lines.append(child)
        elif child.type in ("function_definition", "class_definition",
                            "decorated_definition"):
            break
    if not import_lines:
        return None
    start = import_lines[0].start_point[0] + 1
    end = import_lines[-1].end_point[0] + 1
    text = src[import_lines[0].start_byte:import_lines[-1].end_byte].decode("utf-8", errors="replace")
    return start, end, text


def _extract_class_header(class_node: Node, src: bytes) -> str:
    """Return the class declaration + docstring, not method bodies."""
    lines = _node_text(class_node, src).splitlines()
    # keep up to 20 lines as class header
    return "\n".join(lines[:20])


def _find_methods_python(class_node: Node, src: bytes) -> list[dict]:
    methods = []
    body = next((c for c in class_node.children if c.type == "block"), None)
    if body is None:
        return methods
    for child in body.children:
        if child.type == "function_definition":
            name = _get_child_text(child, "identifier", src)
            s, e = _lines(child)
            methods.append({"name": name, "content": _node_text(child, src),
                            "line_start": s, "line_end": e})
        elif child.type == "decorated_definition":
            inner = next((c for c in child.children if c.type == "function_definition"), None)
            if inner:
                name = _get_child_text(inner, "identifier", src)
                s, e = _lines(child)
                methods.append({"name": name, "content": _node_text(child, src),
                                "line_start": s, "line_end": e})
    return methods


def _get_child_text(node: Node, child_type: str, src: bytes) -> str | None:
    for child in node.children:
        if child.type == child_type:
            return _node_text(child, src)
    return None


# ---------------------------------------------------------------------------
# M2-T04: JavaScript / TypeScript
# ---------------------------------------------------------------------------

def parse_javascript(file_path: str, content: str, language: str) -> list[CodeUnit]:
    ext = Path(file_path).suffix.lower()
    if ext in (".ts",):
        lang_obj = TS_LANGUAGE
    elif ext in (".tsx",):
        lang_obj = TSX_LANGUAGE
    else:
        lang_obj = JS_LANGUAGE

    src = content.encode("utf-8")
    parser = _make_parser(lang_obj)
    tree = parser.parse(src)
    units: list[CodeUnit] = []

    _extract_js_nodes(tree.root_node, src, file_path, language, units, parent_name=None)

    return units if units else _fallback(file_path, language, content)


def _extract_js_nodes(
    node: Node, src: bytes, file_path: str, language: str,
    units: list[CodeUnit], parent_name: str | None
) -> None:
    for child in node.children:
        if child.type == "function_declaration":
            name = _get_child_text(child, "identifier", src)
            s, e = _lines(child)
            units.append(CodeUnit(
                file_path=file_path, language=language,
                chunk_type=ChunkType.FUNCTION if parent_name is None else ChunkType.METHOD,
                name=name, content=_node_text(child, src),
                line_start=s, line_end=e, parent_name=parent_name,
            ))
        elif child.type == "lexical_declaration":
            # const Foo = () => {...} or const Foo = function() {...}
            for decl in child.children:
                if decl.type == "variable_declarator":
                    var_name_node = decl.child_by_field_name("name")
                    val_node = decl.child_by_field_name("value")
                    if val_node and val_node.type in ("arrow_function", "function"):
                        name = _node_text(var_name_node, src) if var_name_node else None
                        s, e = _lines(child)
                        units.append(CodeUnit(
                            file_path=file_path, language=language,
                            chunk_type=ChunkType.FUNCTION,
                            name=name, content=_node_text(child, src),
                            line_start=s, line_end=e, parent_name=parent_name,
                        ))
        elif child.type == "class_declaration":
            class_name = _get_child_text(child, "identifier", src)
            s, e = _lines(child)
            units.append(CodeUnit(
                file_path=file_path, language=language,
                chunk_type=ChunkType.CLASS, name=class_name,
                content=_node_text(child, src)[:500],
                line_start=s, line_end=e,
            ))
            # methods inside class body
            body = next((c for c in child.children if c.type == "class_body"), None)
            if body:
                for method in body.children:
                    if method.type == "method_definition":
                        mname = _get_child_text(method, "property_identifier", src)
                        ms, me = _lines(method)
                        units.append(CodeUnit(
                            file_path=file_path, language=language,
                            chunk_type=ChunkType.METHOD, name=mname,
                            content=_node_text(method, src),
                            line_start=ms, line_end=me, parent_name=class_name,
                        ))
        elif child.type in ("export_statement",):
            # re-recurse into export default / export function
            _extract_js_nodes(child, src, file_path, language, units, parent_name)
        elif child.type in ("interface_declaration", "type_alias_declaration"):
            name = _get_child_text(child, "type_identifier", src)
            s, e = _lines(child)
            units.append(CodeUnit(
                file_path=file_path, language=language,
                chunk_type=ChunkType.BLOCK, name=name,
                content=_node_text(child, src),
                line_start=s, line_end=e,
            ))


# ---------------------------------------------------------------------------
# M2-T05: Go + Java
# ---------------------------------------------------------------------------

def parse_go(file_path: str, content: str) -> list[CodeUnit]:
    src = content.encode("utf-8")
    parser = _make_parser(GO_LANGUAGE)
    tree = parser.parse(src)
    units: list[CodeUnit] = []

    for node in tree.root_node.children:
        if node.type == "function_declaration":
            name = _get_child_text(node, "identifier", src)
            s, e = _lines(node)
            units.append(CodeUnit(
                file_path=file_path, language="go",
                chunk_type=ChunkType.FUNCTION, name=name,
                content=_node_text(node, src), line_start=s, line_end=e,
            ))
        elif node.type == "method_declaration":
            name = _get_child_text(node, "field_identifier", src)
            # receiver type
            recv = next((c for c in node.children if c.type == "parameter_list"), None)
            parent = None
            if recv:
                type_node = _find_deep(recv, {"type_identifier", "pointer_type"})
                if type_node:
                    parent = _node_text(type_node, src).lstrip("*")
            s, e = _lines(node)
            units.append(CodeUnit(
                file_path=file_path, language="go",
                chunk_type=ChunkType.METHOD, name=name,
                content=_node_text(node, src), line_start=s, line_end=e,
                parent_name=parent,
            ))
        elif node.type == "type_declaration":
            for spec in node.children:
                if spec.type == "type_spec":
                    name = _get_child_text(spec, "type_identifier", src)
                    s, e = _lines(node)
                    units.append(CodeUnit(
                        file_path=file_path, language="go",
                        chunk_type=ChunkType.CLASS, name=name,
                        content=_node_text(node, src), line_start=s, line_end=e,
                    ))

    return units if units else _fallback(file_path, "go", content)


def parse_java(file_path: str, content: str) -> list[CodeUnit]:
    src = content.encode("utf-8")
    parser = _make_parser(JAVA_LANGUAGE)
    tree = parser.parse(src)
    units: list[CodeUnit] = []

    for node in tree.root_node.children:
        if node.type == "class_declaration":
            class_name = _get_child_text(node, "identifier", src)
            s, e = _lines(node)
            units.append(CodeUnit(
                file_path=file_path, language="java",
                chunk_type=ChunkType.CLASS, name=class_name,
                content=_node_text(node, src)[:500],
                line_start=s, line_end=e,
            ))
            body = next((c for c in node.children if c.type == "class_body"), None)
            if body:
                for child in body.children:
                    if child.type == "method_declaration":
                        mname = _get_child_text(child, "identifier", src)
                        ms, me = _lines(child)
                        units.append(CodeUnit(
                            file_path=file_path, language="java",
                            chunk_type=ChunkType.METHOD, name=mname,
                            content=_node_text(child, src),
                            line_start=ms, line_end=me, parent_name=class_name,
                        ))

    return units if units else _fallback(file_path, "java", content)


def _find_deep(node: Node, types: set[str]) -> Node | None:
    if node.type in types:
        return node
    for child in node.children:
        found = _find_deep(child, types)
        if found:
            return found
    return None


# ---------------------------------------------------------------------------
# M2-T06: Rust + fallback + dispatcher
# ---------------------------------------------------------------------------

def parse_rust(file_path: str, content: str) -> list[CodeUnit]:
    src = content.encode("utf-8")
    parser = _make_parser(RUST_LANGUAGE)
    tree = parser.parse(src)
    units: list[CodeUnit] = []

    for node in tree.root_node.children:
        if node.type == "function_item":
            name = _get_child_text(node, "identifier", src)
            s, e = _lines(node)
            units.append(CodeUnit(
                file_path=file_path, language="rust",
                chunk_type=ChunkType.FUNCTION, name=name,
                content=_node_text(node, src), line_start=s, line_end=e,
            ))
        elif node.type in ("struct_item", "enum_item", "trait_item", "impl_item"):
            name = _get_child_text(node, "type_identifier", src)
            s, e = _lines(node)
            chunk_type = ChunkType.CLASS if node.type in ("struct_item", "enum_item") else ChunkType.BLOCK
            units.append(CodeUnit(
                file_path=file_path, language="rust",
                chunk_type=chunk_type, name=name,
                content=_node_text(node, src), line_start=s, line_end=e,
            ))

    return units if units else _fallback(file_path, "rust", content)


def _fallback(file_path: str, language: str, content: str) -> list[CodeUnit]:
    """Split content into ~400-line BLOCK chunks with no AST awareness."""
    BLOCK_LINES = 400
    lines = content.splitlines()
    if not lines:
        return [CodeUnit(
            file_path=file_path, language=language,
            chunk_type=ChunkType.BLOCK, name=None,
            content="", line_start=1, line_end=1,
        )]
    units = []
    for i in range(0, len(lines), BLOCK_LINES):
        chunk_lines = lines[i:i + BLOCK_LINES]
        units.append(CodeUnit(
            file_path=file_path, language=language,
            chunk_type=ChunkType.BLOCK, name=None,
            content="\n".join(chunk_lines),
            line_start=i + 1, line_end=i + len(chunk_lines),
        ))
    return units


_EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "python",
    ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "typescript",
    ".go": "go",
    ".java": "java",
    ".rs": "rust",
    ".c": "c", ".cpp": "cpp", ".cs": "csharp",
    ".rb": "ruby", ".php": "php",
    ".md": "markdown", ".yaml": "yaml", ".yml": "yaml",
    ".toml": "toml", ".json": "json", ".sql": "sql", ".sh": "bash",
}


def parse_file(file_path: str, content: str) -> list[CodeUnit]:
    """Dispatch to the correct parser by file extension."""
    ext = Path(file_path).suffix.lower()
    language = _EXT_TO_LANGUAGE.get(ext, "text")

    try:
        if ext == ".py":
            return parse_python(file_path, content)
        if ext in (".js", ".jsx"):
            return parse_javascript(file_path, content, "javascript")
        if ext in (".ts", ".tsx"):
            return parse_javascript(file_path, content, "typescript")
        if ext == ".go":
            return parse_go(file_path, content)
        if ext == ".java":
            return parse_java(file_path, content)
        if ext == ".rs":
            return parse_rust(file_path, content)
    except Exception:
        pass  # fall through to fallback on any parser error

    return _fallback(file_path, language, content)
