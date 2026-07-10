"use client";

import { useEffect, useState, useCallback } from "react";
import Link from "next/link";
import { useParams, usePathname } from "next/navigation";
import { MessageSquare, ArrowLeft, X, ChevronRight, Zap, GitBranch } from "lucide-react";
import { toast } from "sonner";
import { FileExplorer } from "@/components/FileExplorer";
import { CodeViewer } from "@/components/CodeViewer";
import { getFileTree, getFileContent, type FileNode } from "@/lib/api";
import { useProjectStore } from "@/lib/projectStore";

export default function ProjectLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const { id } = useParams<{ id: string }>();
  const pathname = usePathname();
  const projectId = Number(id);

  const [tree, setTree] = useState<FileNode[]>([]);
  const [treeLoading, setTreeLoading] = useState(true);
  const [explorerOpen, setExplorerOpen] = useState(true);

  const { openFile, setOpenFile, clearFile } = useProjectStore();

  useEffect(() => {
    getFileTree(projectId)
      .then((res) => setTree(res.tree))
      .catch(() => {/* project might not be ready yet */})
      .finally(() => setTreeLoading(false));
  }, [projectId]);

  const handleFileClick = useCallback(
    async (path: string) => {
      try {
        const res = await getFileContent(projectId, path);
        setOpenFile({
          path,
          content: res.content,
          language: res.language,
          line_count: res.line_count,
          highlightFrom: null,
          highlightTo: null,
        });
      } catch {
        toast.error("Failed to load file.");
      }
    },
    [projectId, setOpenFile]
  );

  const navItems = [
    { label: "Chat", href: `/projects/${id}/chat`, icon: MessageSquare },
    { label: "Generate", href: `/projects/${id}/generate`, icon: Zap },
    { label: "Graph", href: `/projects/${id}/graph`, icon: GitBranch },
  ];

  return (
    <div className="h-screen flex flex-col bg-background overflow-hidden">
      {/* Top bar */}
      <header className="border-b shrink-0 h-[49px] flex items-center">
        <div className="px-4 flex items-center gap-3 w-full">
          <Link
            href="/dashboard"
            className="flex items-center gap-1.5 text-sm text-muted-foreground hover:text-foreground transition-colors shrink-0"
          >
            <ArrowLeft size={15} />
            Dashboard
          </Link>
          <span className="text-muted-foreground/30">|</span>
          <nav className="flex items-center gap-1">
            {navItems.map(({ label, href, icon: Icon }) => {
              const active = pathname.startsWith(href);
              return (
                <Link
                  key={href}
                  href={href}
                  className={`flex items-center gap-1.5 px-3 py-1.5 rounded-md text-sm font-medium transition-colors ${
                    active
                      ? "bg-accent text-accent-foreground"
                      : "text-muted-foreground hover:text-foreground hover:bg-accent/50"
                  }`}
                >
                  <Icon size={15} />
                  {label}
                </Link>
              );
            })}
          </nav>

          {/* Toggle explorer button */}
          <button
            onClick={() => setExplorerOpen((v) => !v)}
            className="ml-auto text-xs text-muted-foreground hover:text-foreground flex items-center gap-1 transition-colors"
          >
            <ChevronRight
              size={14}
              className={`transition-transform ${explorerOpen ? "rotate-180" : ""}`}
            />
            Files
          </button>
        </div>
      </header>

      {/* Body: explorer | main | code viewer */}
      <div className="flex flex-1 min-h-0">
        {/* File explorer sidebar */}
        {explorerOpen && (
          <aside className="w-56 border-r shrink-0 flex flex-col overflow-hidden">
            <div className="px-3 py-2 border-b">
              <p className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Files
              </p>
            </div>
            <div className="flex-1 overflow-y-auto">
              {treeLoading ? (
                <div className="px-3 py-2 space-y-1.5">
                  {[80, 60, 70, 55, 65, 50].map((w, i) => (
                    <div
                      key={i}
                      className="h-4 rounded bg-muted animate-pulse"
                      style={{ width: `${w}%` }}
                    />
                  ))}
                </div>
              ) : (
                <FileExplorer
                  tree={tree}
                  onFileClick={handleFileClick}
                  activeFile={openFile?.path}
                />
              )}
            </div>
          </aside>
        )}

        {/* Page content (chat, etc.) */}
        <div className="flex-1 min-w-0 flex flex-col overflow-hidden">
          {children}
        </div>

        {/* Code viewer panel — slides in when a file is open */}
        {openFile && (
          <div className="w-[45%] border-l flex flex-col shrink-0 overflow-hidden">
            {/* Code viewer header */}
            <div className="h-9 border-b flex items-center px-3 gap-2 shrink-0 bg-muted/30">
              <span className="text-xs font-mono text-muted-foreground truncate flex-1">
                {openFile.path}
              </span>
              {openFile.highlightFrom && (
                <span className="text-xs text-yellow-500 shrink-0">
                  :{openFile.highlightFrom}–{openFile.highlightTo ?? openFile.highlightFrom}
                </span>
              )}
              <button
                onClick={clearFile}
                className="shrink-0 text-muted-foreground hover:text-foreground transition-colors"
              >
                <X size={14} />
              </button>
            </div>
            <div className="flex-1 overflow-hidden">
              <CodeViewer
                content={openFile.content}
                language={openFile.language}
                highlightFrom={openFile.highlightFrom}
                highlightTo={openFile.highlightTo}
              />
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
