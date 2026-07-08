"""Language map: file extension → tree-sitter Language object."""
import tree_sitter_python as _tspython
import tree_sitter_javascript as _tsjs
import tree_sitter_typescript as _tsts
import tree_sitter_go as _tsgo
import tree_sitter_java as _tsjava
import tree_sitter_rust as _tsrust
from tree_sitter import Language

PY_LANGUAGE = Language(_tspython.language())
JS_LANGUAGE = Language(_tsjs.language())
TS_LANGUAGE = Language(_tsts.language_typescript())
TSX_LANGUAGE = Language(_tsts.language_tsx())
GO_LANGUAGE = Language(_tsgo.language())
JAVA_LANGUAGE = Language(_tsjava.language())
RUST_LANGUAGE = Language(_tsrust.language())

LANGUAGE_MAP: dict[str, Language] = {
    ".py": PY_LANGUAGE,
    ".js": JS_LANGUAGE,
    ".jsx": JS_LANGUAGE,
    ".ts": TS_LANGUAGE,
    ".tsx": TSX_LANGUAGE,
    ".go": GO_LANGUAGE,
    ".java": JAVA_LANGUAGE,
    ".rs": RUST_LANGUAGE,
}
