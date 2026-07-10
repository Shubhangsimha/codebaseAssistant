"use client";

import { useState } from "react";
import {
  ChevronRight,
  ChevronDown,
  FileCode,
  Folder,
  FolderOpen,
} from "lucide-react";
import type { FileNode } from "@/lib/api";

interface FileExplorerProps {
  tree: FileNode[];
  onFileClick: (path: string) => void;
  activeFile?: string | null;
}

const LANG_COLORS: Record<string, string> = {
  Python: "text-blue-400",
  JavaScript: "text-yellow-400",
  TypeScript: "text-blue-500",
  Go: "text-cyan-400",
  Java: "text-orange-400",
  Kotlin: "text-purple-400",
  Rust: "text-orange-600",
  "C++": "text-pink-400",
  C: "text-gray-400",
  "C#": "text-green-500",
  Ruby: "text-red-400",
  PHP: "text-indigo-400",
  Markdown: "text-gray-300",
  JSON: "text-green-400",
  YAML: "text-yellow-300",
  SQL: "text-teal-400",
  Shell: "text-green-300",
};

function langColor(lang?: string | null): string {
  return lang ? (LANG_COLORS[lang] ?? "text-muted-foreground") : "text-muted-foreground";
}

interface TreeNodeProps {
  node: FileNode;
  depth: number;
  onFileClick: (path: string) => void;
  activeFile?: string | null;
}

function TreeNode({ node, depth, onFileClick, activeFile }: TreeNodeProps) {
  const [open, setOpen] = useState(depth === 0);
  const indent = depth * 12;

  if (node.type === "directory") {
    return (
      <div>
        <button
          onClick={() => setOpen((v) => !v)}
          className="w-full flex items-center gap-1 px-2 py-0.5 text-xs text-muted-foreground hover:text-foreground hover:bg-accent/40 rounded transition-colors"
          style={{ paddingLeft: `${indent + 8}px` }}
        >
          {open ? (
            <ChevronDown size={12} className="shrink-0" />
          ) : (
            <ChevronRight size={12} className="shrink-0" />
          )}
          {open ? (
            <FolderOpen size={13} className="shrink-0 text-yellow-400/80" />
          ) : (
            <Folder size={13} className="shrink-0 text-yellow-400/60" />
          )}
          <span className="truncate font-medium">
            {node.path.split("/").pop()}
          </span>
        </button>

        {open && node.children && (
          <div>
            {node.children.map((child) => (
              <TreeNode
                key={child.path}
                node={child}
                depth={depth + 1}
                onFileClick={onFileClick}
                activeFile={activeFile}
              />
            ))}
          </div>
        )}
      </div>
    );
  }

  const filename = node.path.split("/").pop() ?? node.path;
  const isActive = activeFile === node.path;

  return (
    <button
      onClick={() => onFileClick(node.path)}
      className={`w-full flex items-center gap-1.5 px-2 py-0.5 text-xs rounded transition-colors ${
        isActive
          ? "bg-accent text-accent-foreground"
          : "text-muted-foreground hover:text-foreground hover:bg-accent/30"
      }`}
      style={{ paddingLeft: `${indent + 20}px` }}
      title={node.path}
    >
      <FileCode size={12} className={`shrink-0 ${langColor(node.language)}`} />
      <span className="truncate">{filename}</span>
      {node.line_count != null && (
        <span className="ml-auto shrink-0 opacity-40 text-[10px]">
          {node.line_count}L
        </span>
      )}
    </button>
  );
}

export function FileExplorer({
  tree,
  onFileClick,
  activeFile,
}: FileExplorerProps) {
  if (tree.length === 0) {
    return (
      <p className="text-xs text-muted-foreground px-3 py-4 text-center">
        No files
      </p>
    );
  }

  return (
    <div className="py-1">
      {tree.map((node) => (
        <TreeNode
          key={node.path}
          node={node}
          depth={0}
          onFileClick={onFileClick}
          activeFile={activeFile}
        />
      ))}
    </div>
  );
}
