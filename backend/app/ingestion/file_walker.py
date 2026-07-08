import logging
from pathlib import Path
from typing import TypedDict

import pathspec

logger = logging.getLogger(__name__)

SUPPORTED_EXTENSIONS: frozenset[str] = frozenset({
    # Python
    ".py", ".pyw",
    # JavaScript / TypeScript
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    # Go
    ".go",
    # Java / Kotlin
    ".java", ".kt",
    # Rust
    ".rs",
    # C / C++
    ".c", ".cpp", ".cc", ".h", ".hpp",
    # C#
    ".cs",
    # Ruby
    ".rb",
    # PHP
    ".php",
    # Config / data
    ".json", ".yaml", ".yml", ".toml",
    # Docs / markup
    ".md", ".mdx", ".rst",
    # SQL
    ".sql",
    # Shell
    ".sh", ".bash", ".zsh",
})

# Bare filenames (no extension) that are worth indexing
SUPPORTED_BARE_NAMES: frozenset[str] = frozenset({
    "Dockerfile", "Makefile", "Jenkinsfile",
})

EXCLUDED_DIRS: frozenset[str] = frozenset({
    "node_modules", ".git", ".svn", ".hg",
    "dist", "build", "out", "__pycache__",
    ".pytest_cache", ".mypy_cache", ".ruff_cache",
    "venv", ".venv", "env", ".env",
    ".next", ".nuxt", ".cache",
    "coverage", ".coverage",
    "target",        # Rust / Java build output
    "vendor",        # Go / PHP dependencies
    ".idea", ".vscode",
    "eggs", ".eggs", "*.egg-info",
})

MAX_FILE_SIZE_BYTES: int = 200_000  # 200 KB

# Map of extension → language display name
EXT_TO_LANGUAGE: dict[str, str] = {
    ".py": "Python", ".pyw": "Python",
    ".js": "JavaScript", ".jsx": "JavaScript",
    ".mjs": "JavaScript", ".cjs": "JavaScript",
    ".ts": "TypeScript", ".tsx": "TypeScript",
    ".go": "Go",
    ".java": "Java", ".kt": "Kotlin",
    ".rs": "Rust",
    ".c": "C", ".h": "C",
    ".cpp": "C++", ".cc": "C++", ".hpp": "C++",
    ".cs": "C#",
    ".rb": "Ruby",
    ".php": "PHP",
    ".json": "JSON",
    ".yaml": "YAML", ".yml": "YAML",
    ".toml": "TOML",
    ".md": "Markdown", ".mdx": "Markdown", ".rst": "reStructuredText",
    ".sql": "SQL",
    ".sh": "Shell", ".bash": "Shell", ".zsh": "Shell",
}


class FileEntry(TypedDict):
    path: Path           # absolute path
    relative_path: str   # relative to repo root, forward-slash separated
    language: str
    size_bytes: int


def walk_files(root: Path) -> list[FileEntry]:
    """Return all source files under root that pass the inclusion filters.

    Filters applied (in order):
    1. Skip excluded directories
    2. Only include supported extensions / bare names
    3. Skip files larger than MAX_FILE_SIZE_BYTES
    4. Respect .gitignore patterns at the root
    """
    root = root.resolve()
    gitignore_spec = _load_gitignore(root)

    entries: list[FileEntry] = []
    skipped_dirs = 0
    skipped_size = 0
    skipped_gitignore = 0

    for file_path in root.rglob("*"):
        if not file_path.is_file():
            continue

        relative = file_path.relative_to(root)
        relative_str = relative.as_posix()

        # 1. Skip if any parent directory is in the exclusion list
        if any(part in EXCLUDED_DIRS for part in relative.parts[:-1]):
            skipped_dirs += 1
            continue

        # 2. Extension / bare-name filter
        ext = file_path.suffix.lower()
        bare = file_path.name
        if ext not in SUPPORTED_EXTENSIONS and bare not in SUPPORTED_BARE_NAMES:
            continue

        # 3. Size filter
        try:
            size = file_path.stat().st_size
        except OSError:
            continue
        if size > MAX_FILE_SIZE_BYTES:
            skipped_size += 1
            continue

        # 4. .gitignore filter
        if gitignore_spec and gitignore_spec.match_file(relative_str):
            skipped_gitignore += 1
            continue

        language = EXT_TO_LANGUAGE.get(ext, bare if bare in SUPPORTED_BARE_NAMES else "Unknown")
        entries.append(
            FileEntry(
                path=file_path,
                relative_path=relative_str,
                language=language,
                size_bytes=size,
            )
        )

    logger.info(
        "File walk complete: %d files kept, %d dirs excluded, "
        "%d too large, %d gitignored",
        len(entries), skipped_dirs, skipped_size, skipped_gitignore,
    )
    return entries


def _load_gitignore(root: Path) -> pathspec.PathSpec | None:
    gitignore_path = root / ".gitignore"
    if not gitignore_path.exists():
        return None
    patterns = gitignore_path.read_text(encoding="utf-8", errors="ignore").splitlines()
    return pathspec.PathSpec.from_lines("gitwildmatch", patterns)
