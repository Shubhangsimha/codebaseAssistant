from __future__ import annotations

import re
from pathlib import Path, PurePosixPath


# ---------------------------------------------------------------------------
# Import extraction patterns per language
# ---------------------------------------------------------------------------

# Python: import foo, from foo.bar import baz
_PY_IMPORT = re.compile(
    r'^\s*(?:from\s+([\w.]+)\s+import|import\s+([\w.,\s]+))',
    re.MULTILINE,
)

# JS/TS: import ... from '...', require('...')
_JS_IMPORT = re.compile(
    r'(?:import\s+.*?from\s+["\']([^"\']+)["\']|require\s*\(\s*["\']([^"\']+)["\']\s*\))',
    re.MULTILINE,
)

# Go: import "pkg" or import ("pkg1" "pkg2")
_GO_IMPORT = re.compile(r'"([^"]+)"', re.MULTILINE)

# Java: import foo.bar.Baz;
_JAVA_IMPORT = re.compile(r'^\s*import\s+([\w.]+)\s*;', re.MULTILINE)


def extract_imports(file_path: str, content: str) -> list[str]:
    """Return list of raw import strings found in the file."""
    ext = Path(file_path).suffix.lower()
    if ext in (".py", ".pyw"):
        return _extract_py(content)
    if ext in (".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs"):
        return _extract_js(content)
    if ext == ".go":
        return _extract_go(content)
    if ext in (".java", ".kt"):
        return _extract_java(content)
    return []


def _extract_py(content: str) -> list[str]:
    results = []
    for m in _PY_IMPORT.finditer(content):
        pkg = m.group(1) or m.group(2)
        if pkg:
            for p in pkg.split(","):
                results.append(p.strip().split(" ")[0])
    return results


def _extract_js(content: str) -> list[str]:
    results = []
    for m in _JS_IMPORT.finditer(content):
        raw = m.group(1) or m.group(2)
        if raw:
            results.append(raw)
    return results


def _extract_go(content: str) -> list[str]:
    # Only grab import blocks
    import_block = re.search(r'import\s*\(([^)]+)\)', content, re.DOTALL)
    single = re.findall(r'^import\s+"([^"]+)"', content, re.MULTILINE)
    results = list(single)
    if import_block:
        results += _GO_IMPORT.findall(import_block.group(1))
    return results


def _extract_java(content: str) -> list[str]:
    return [m.group(1) for m in _JAVA_IMPORT.finditer(content)]


# ---------------------------------------------------------------------------
# Graph builder
# ---------------------------------------------------------------------------

def build_dependency_graph(
    file_contents: dict[str, str],
) -> dict[str, list[str]]:
    """
    Build adjacency list: {source_file: [dep_file, ...]}
    Only includes edges where the dependency resolves to another file in the project.
    """
    all_files = set(file_contents.keys())
    # Index: module/bare-name → file path for fast lookup
    module_index = _build_import_to_filepath_map(all_files)

    graph: dict[str, list[str]] = {}
    for file_path, content in file_contents.items():
        raw_imports = extract_imports(file_path, content)
        resolved = []
        for imp in raw_imports:
            target = _resolve(imp, file_path, all_files, module_index)
            if target and target != file_path:
                resolved.append(target)
        graph[file_path] = list(dict.fromkeys(resolved))  # dedupe, preserve order

    return graph


def _build_import_to_filepath_map(files: set[str]) -> dict[str, str]:
    """Map stem/module-path → file path."""
    idx: dict[str, str] = {}
    for f in files:
        p = PurePosixPath(f)
        # bare stem: auth → backend/auth.py
        idx[p.stem] = f
        # dotted: backend.auth → backend/auth.py
        dotted = str(p.with_suffix("")).replace("/", ".")
        idx[dotted] = f
        # forward-slash path without extension
        idx[str(p.with_suffix(""))] = f
    return idx


def _resolve(
    raw: str,
    source: str,
    all_files: set[str],
    module_index: dict[str, str],
) -> str | None:
    """Try to map a raw import string to a file path in the project."""
    # Relative JS/TS imports: ./foo, ../bar/baz
    if raw.startswith("./") or raw.startswith("../"):
        base = PurePosixPath(source).parent
        # Resolve the relative path manually without touching the filesystem
        candidate = str((base / raw).as_posix())
        # Normalize ../ by splitting and collapsing
        parts = []
        for part in candidate.split("/"):
            if part == "..":
                if parts:
                    parts.pop()
            elif part and part != ".":
                parts.append(part)
        candidate = "/".join(parts)
        # try with common extensions
        for ext in ("", ".js", ".jsx", ".ts", ".tsx", "/index.js", "/index.ts"):
            full = candidate + ext
            if full in all_files:
                return full
        return None

    # External packages (no slash prefix, not relative) — skip
    if not raw.startswith("."):
        # Check module index for project-internal matches
        cleaned = raw.replace("/", ".").split(" ")[0]
        return module_index.get(cleaned) or module_index.get(raw.split("/")[0])

    return None
