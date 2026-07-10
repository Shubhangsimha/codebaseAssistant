"use client";

import { useState } from "react";
import { useParams } from "next/navigation";
import { Loader2, Zap, Globe, FileText, Copy, Check } from "lucide-react";
import { toast } from "sonner";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import {
  getArchitecture,
  getApiEndpoints,
  getDocstringStreamUrl,
  searchChunks,
  type ArchitectureResult,
  type ApiEndpoint,
  type ChunkResult,
} from "@/lib/api";
import { METHOD_COLORS } from "@/lib/constants";

// ---------------------------------------------------------------------------
// Copy button
// ---------------------------------------------------------------------------
function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false);
  function handleCopy() {
    navigator.clipboard.writeText(text);
    setCopied(true);
    setTimeout(() => setCopied(false), 1800);
  }
  return (
    <button
      onClick={handleCopy}
      className="p-1 rounded text-muted-foreground hover:text-foreground transition-colors"
    >
      {copied ? <Check size={14} /> : <Copy size={14} />}
    </button>
  );
}

// ---------------------------------------------------------------------------
// Architecture panel
// ---------------------------------------------------------------------------
function ArchitecturePanel({ projectId }: { projectId: number }) {
  const [data, setData] = useState<ArchitectureResult | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    try {
      const result = await getArchitecture(projectId);
      setData(result);
    } catch (e: unknown) {
      toast.error((e as { message?: string })?.message ?? "Architecture generation failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="border rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Zap size={16} className="text-yellow-500" />
          <h2 className="font-semibold">Architecture Summary</h2>
        </div>
        <Button size="sm" onClick={run} disabled={loading}>
          {loading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : null}
          {data ? "Regenerate" : "Generate"}
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Analyzing codebase…
        </div>
      )}

      {data && !loading && (
        <div className="space-y-4">
          <p className="text-sm leading-relaxed">{data.summary}</p>

          {data.stack.length > 0 && (
            <div>
              <p className="text-xs font-medium text-muted-foreground mb-1.5 uppercase tracking-wider">Stack</p>
              <div className="flex flex-wrap gap-1.5">
                {data.stack.map((s) => (
                  <Badge key={s} variant="secondary" className="text-xs">{s}</Badge>
                ))}
              </div>
            </div>
          )}

          {data.layers.length > 0 && (
            <div className="space-y-2">
              <p className="text-xs font-medium text-muted-foreground mb-1 uppercase tracking-wider">Layers</p>
              {data.layers.map((layer) => (
                <div key={layer.name} className="bg-muted/40 rounded-lg px-4 py-3">
                  <p className="text-sm font-medium">{layer.name}</p>
                  <p className="text-xs text-muted-foreground mt-0.5">{layer.description}</p>
                  {layer.examples.length > 0 && (
                    <div className="flex flex-wrap gap-1 mt-1.5">
                      {layer.examples.map((ex) => (
                        <code key={ex} className="text-[11px] bg-background rounded px-1.5 py-0.5 font-mono">
                          {ex}
                        </code>
                      ))}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// API Endpoints panel
// ---------------------------------------------------------------------------
function ApiEndpointsPanel({ projectId }: { projectId: number }) {
  const [endpoints, setEndpoints] = useState<ApiEndpoint[] | null>(null);
  const [loading, setLoading] = useState(false);

  async function run() {
    setLoading(true);
    try {
      const result = await getApiEndpoints(projectId);
      setEndpoints(result);
    } catch (e: unknown) {
      toast.error((e as { message?: string })?.message ?? "API scan failed");
    } finally {
      setLoading(false);
    }
  }

  return (
    <section className="border rounded-xl p-5 space-y-4">
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <Globe size={16} className="text-blue-500" />
          <h2 className="font-semibold">API Endpoints</h2>
        </div>
        <Button size="sm" onClick={run} disabled={loading}>
          {loading ? <Loader2 size={14} className="animate-spin mr-1.5" /> : null}
          {endpoints !== null ? "Rescan" : "Scan"}
        </Button>
      </div>

      {loading && (
        <div className="flex items-center gap-2 text-sm text-muted-foreground">
          <Loader2 size={14} className="animate-spin" />
          Scanning for routes…
        </div>
      )}

      {endpoints !== null && !loading && (
        endpoints.length === 0 ? (
          <p className="text-sm text-muted-foreground">No API endpoints detected.</p>
        ) : (
          <div className="space-y-1.5">
            <p className="text-xs text-muted-foreground">{endpoints.length} endpoints found</p>
            {endpoints.map((ep, i) => {
              const colorClass = METHOD_COLORS[ep.method] ?? "bg-muted text-muted-foreground";
              return (
                <div key={i} className="flex items-start gap-3 px-3 py-2 rounded-lg hover:bg-muted/40 transition-colors">
                  <span className={`text-[11px] font-bold font-mono px-1.5 py-0.5 rounded border shrink-0 ${colorClass}`}>
                    {ep.method}
                  </span>
                  <div className="min-w-0">
                    <code className="text-sm font-mono">{ep.path}</code>
                    {ep.handler && (
                      <span className="text-xs text-muted-foreground ml-2">→ {ep.handler}</span>
                    )}
                    {ep.description && (
                      <p className="text-xs text-muted-foreground mt-0.5">{ep.description}</p>
                    )}
                  </div>
                </div>
              );
            })}
          </div>
        )
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Doc Generator panel
// ---------------------------------------------------------------------------
function DocGeneratorPanel({ projectId }: { projectId: number }) {
  const [query, setQuery] = useState("");
  const [chunks, setChunks] = useState<ChunkResult[]>([]);
  const [searching, setSearching] = useState(false);
  const [selectedChunk, setSelectedChunk] = useState<ChunkResult | null>(null);
  const [docstring, setDocstring] = useState("");
  const [generating, setGenerating] = useState(false);

  async function handleSearch() {
    if (!query.trim()) return;
    setSearching(true);
    setChunks([]);
    setSelectedChunk(null);
    setDocstring("");
    try {
      const results = await searchChunks(projectId, query, 10);
      // Only show functions/methods/classes
      setChunks(results.filter(c => ["function","method","class"].includes(c.chunk_type)));
    } catch {
      toast.error("Search failed");
    } finally {
      setSearching(false);
    }
  }

  async function generateDoc(chunk: ChunkResult) {
    setSelectedChunk(chunk);
    setDocstring("");
    setGenerating(true);

    try {
      const res = await fetch(getDocstringStreamUrl(projectId, chunk.chunk_id));
      if (!res.ok || !res.body) { toast.error("Failed to start generation"); setGenerating(false); return; }

      const reader = res.body.getReader();
      const decoder = new TextDecoder();
      let buf = "";

      while (true) {
        const { done, value } = await reader.read();
        if (done) break;
        buf += decoder.decode(value, { stream: true });
        const lines = buf.split("\n");
        buf = lines.pop() ?? "";
        for (const line of lines) {
          if (!line.startsWith("data: ")) continue;
          try {
            const ev = JSON.parse(line.slice(6));
            if (ev.type === "token") setDocstring(p => p + ev.content);
            if (ev.type === "error") { toast.error(ev.message); break; }
          } catch { /* ignore */ }
        }
      }
    } catch {
      toast.error("Generation failed");
      setSelectedChunk(null);
    } finally {
      setGenerating(false);
    }
  }

  return (
    <section className="border rounded-xl p-5 space-y-4">
      <div className="flex items-center gap-2">
        <FileText size={16} className="text-green-500" />
        <h2 className="font-semibold">Documentation Generator</h2>
      </div>
      <p className="text-xs text-muted-foreground">Search for a function or class to generate its docstring.</p>

      <div className="flex gap-2">
        <input
          value={query}
          onChange={e => setQuery(e.target.value)}
          onKeyDown={e => e.key === "Enter" && handleSearch()}
          placeholder="Search functions… e.g. authenticate user"
          className="flex-1 text-sm border rounded-md px-3 py-1.5 bg-background focus:outline-none focus:ring-2 focus:ring-ring"
        />
        <Button size="sm" onClick={handleSearch} disabled={searching || !query.trim()}>
          {searching ? <Loader2 size={13} className="animate-spin" /> : "Search"}
        </Button>
      </div>

      {chunks.length > 0 && (
        <div className="space-y-1 max-h-48 overflow-y-auto">
          {chunks.map(chunk => (
            <button
              key={chunk.chunk_id}
              onClick={() => generateDoc(chunk)}
              disabled={generating}
              className={`w-full text-left px-3 py-2 rounded-lg text-sm transition-colors hover:bg-accent/50 ${
                selectedChunk?.chunk_id === chunk.chunk_id ? "bg-accent" : ""
              }`}
            >
              <span className="font-mono font-medium">{chunk.name || "(anonymous)"}</span>
              <span className="text-xs text-muted-foreground ml-2">{chunk.chunk_type}</span>
              <span className="text-xs text-muted-foreground ml-2 truncate block">{chunk.file_path}</span>
            </button>
          ))}
        </div>
      )}

      {(docstring || generating) && (
        <div className="bg-muted/40 rounded-lg p-3 relative">
          <div className="absolute top-2 right-2 flex items-center gap-1">
            {generating && <Loader2 size={12} className="animate-spin text-muted-foreground" />}
            {docstring && !generating && <CopyButton text={docstring} />}
          </div>
          <pre className="text-xs font-mono whitespace-pre-wrap leading-relaxed pr-6">
            {docstring}
            {generating && <span className="animate-pulse">▌</span>}
          </pre>
        </div>
      )}
    </section>
  );
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------
export default function GeneratePage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  return (
    <div className="h-full overflow-y-auto">
      <div className="max-w-3xl mx-auto px-6 py-8 space-y-6">
        <div>
          <h1 className="text-xl font-bold">Generate</h1>
          <p className="text-sm text-muted-foreground mt-1">One-click intelligence about this codebase.</p>
        </div>
        <ArchitecturePanel projectId={projectId} />
        <ApiEndpointsPanel projectId={projectId} />
        <DocGeneratorPanel projectId={projectId} />
      </div>
    </div>
  );
}
