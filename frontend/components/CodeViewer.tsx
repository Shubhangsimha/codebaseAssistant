"use client";

import { useEffect, useRef } from "react";
import CodeMirror, { EditorView } from "@uiw/react-codemirror";
import { oneDark } from "@codemirror/theme-one-dark";
import { python } from "@codemirror/lang-python";
import { javascript } from "@codemirror/lang-javascript";
import { java } from "@codemirror/lang-java";
import { go } from "@codemirror/lang-go";
import { rust } from "@codemirror/lang-rust";
import { cpp } from "@codemirror/lang-cpp";
import { markdown } from "@codemirror/lang-markdown";
import { sql } from "@codemirror/lang-sql";
import { json } from "@codemirror/lang-json";
import { Decoration, DecorationSet, ViewPlugin, ViewUpdate } from "@codemirror/view";
import { StateEffect, StateField, RangeSetBuilder } from "@codemirror/state";
import type { Extension } from "@codemirror/state";

// ---------------------------------------------------------------------------
// Highlight line effect
// ---------------------------------------------------------------------------

const setHighlightLines = StateEffect.define<{ from: number; to: number } | null>();

const highlightField = StateField.define<DecorationSet>({
  create: () => Decoration.none,
  update(deco, tr) {
    for (const e of tr.effects) {
      if (e.is(setHighlightLines)) {
        if (!e.value) return Decoration.none;
        const { from, to } = e.value;
        const builder = new RangeSetBuilder<Decoration>();
        const mark = Decoration.line({ class: "cm-highlighted-line" });
        for (let line = from; line <= to; line++) {
          try {
            const lineObj = tr.state.doc.line(line);
            builder.add(lineObj.from, lineObj.from, mark);
          } catch {
            // line out of range
          }
        }
        return builder.finish();
      }
    }
    return deco.map(tr.changes);
  },
  provide: (f) => EditorView.decorations.from(f),
});

const highlightStyle = EditorView.baseTheme({
  ".cm-highlighted-line": {
    backgroundColor: "rgba(255, 200, 0, 0.12) !important",
    borderLeft: "2px solid rgba(255, 200, 0, 0.6)",
  },
});

// ---------------------------------------------------------------------------
// Language extension map
// ---------------------------------------------------------------------------

function langExtension(language?: string | null): Extension {
  switch (language?.toLowerCase()) {
    case "python": return python();
    case "javascript": return javascript({ jsx: true });
    case "typescript": return javascript({ typescript: true, jsx: true });
    case "java": return java();
    case "go": return go();
    case "rust": return rust();
    case "c":
    case "c++": return cpp();
    case "markdown": return markdown();
    case "sql": return sql();
    case "json": return json();
    default: return [];
  }
}

// ---------------------------------------------------------------------------
// Component
// ---------------------------------------------------------------------------

interface CodeViewerProps {
  content: string;
  language?: string | null;
  highlightFrom?: number | null;
  highlightTo?: number | null;
}

export function CodeViewer({
  content,
  language,
  highlightFrom,
  highlightTo,
}: CodeViewerProps) {
  const viewRef = useRef<ReturnType<typeof EditorView.prototype.state.toJSON> | null>(null);
  // We need a ref to the actual EditorView instance
  const editorViewRef = useRef<EditorView | null>(null);

  // Clear highlight when content changes (new file opened)
  useEffect(() => {
    const view = editorViewRef.current;
    if (!view) return;
    view.dispatch({ effects: setHighlightLines.of(null) });
  }, [content]);

  // Scroll to and highlight lines when highlight props change
  useEffect(() => {
    const view = editorViewRef.current;
    if (!view || !highlightFrom) return;

    const from = highlightFrom;
    const to = highlightTo ?? highlightFrom;

    view.dispatch({ effects: setHighlightLines.of({ from, to }) });

    try {
      const lineObj = view.state.doc.line(from);
      view.dispatch({
        effects: EditorView.scrollIntoView(lineObj.from, { y: "center" }),
      });
    } catch {
      // line out of range — ignore
    }
  }, [highlightFrom, highlightTo]);

  const extensions: Extension[] = [
    langExtension(language),
    highlightField,
    highlightStyle,
    EditorView.lineWrapping,
    EditorView.editable.of(false),
  ];

  return (
    <CodeMirror
      value={content}
      theme={oneDark}
      extensions={extensions}
      readOnly
      basicSetup={{
        lineNumbers: true,
        foldGutter: true,
        highlightActiveLine: false,
        highlightSelectionMatches: false,
        autocompletion: false,
        searchKeymap: false,
      }}
      onCreateEditor={(view) => {
        editorViewRef.current = view;
      }}
      style={{ height: "100%", overflow: "auto", fontSize: "13px" }}
    />
  );
}
