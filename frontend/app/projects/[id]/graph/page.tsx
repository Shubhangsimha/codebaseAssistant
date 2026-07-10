"use client";

import { useEffect, useState, useCallback } from "react";
import { useParams } from "next/navigation";
import { Loader2, AlertTriangle } from "lucide-react";
import { toast } from "sonner";
import {
  ReactFlow,
  ReactFlowProvider,
  Background,
  Controls,
  MiniMap,
  useNodesState,
  useEdgesState,
  type Node,
  type Edge,
} from "@xyflow/react";
import "@xyflow/react/dist/style.css";
import { getDependencyGraph, getFileContent, type GraphNode, type GraphEdge } from "@/lib/api";
import { useProjectStore } from "@/lib/projectStore";

// ---------------------------------------------------------------------------
// Layout: simple layered position using topological sort approximation
// ---------------------------------------------------------------------------

function layoutNodes(nodes: GraphNode[], edges: GraphEdge[]): Node[] {
  const inDegree: Record<string, number> = {};
  const outEdges: Record<string, string[]> = {};

  for (const n of nodes) {
    inDegree[n.id] = 0;
    outEdges[n.id] = [];
  }
  for (const e of edges) {
    inDegree[e.target] = (inDegree[e.target] || 0) + 1;
    outEdges[e.source] = outEdges[e.source] || [];
    outEdges[e.source].push(e.target);
  }

  // BFS layers
  const layers: string[][] = [];
  const assigned = new Set<string>();
  let current = nodes.map(n => n.id).filter(id => inDegree[id] === 0);

  while (current.length > 0) {
    layers.push(current);
    current.forEach(id => assigned.add(id));
    const next: string[] = [];
    for (const id of current) {
      for (const t of outEdges[id] || []) {
        inDegree[t]--;
        if (inDegree[t] === 0 && !assigned.has(t)) next.push(t);
      }
    }
    current = next;
  }

  // Any remaining (cycles)
  const remaining = nodes.map(n => n.id).filter(id => !assigned.has(id));
  if (remaining.length > 0) layers.push(remaining);

  const X_GAP = 240;
  const Y_GAP = 120;
  const positions: Record<string, { x: number; y: number }> = {};

  for (let li = 0; li < layers.length; li++) {
    const layer = layers[li];
    const startX = -(layer.length * X_GAP) / 2;
    for (let ni = 0; ni < layer.length; ni++) {
      positions[layer[ni]] = { x: startX + ni * X_GAP, y: li * Y_GAP };
    }
  }

  return nodes.map(n => ({
    id: n.id,
    data: n.data,
    position: positions[n.id] ?? { x: 0, y: 0 },
    style: n.data.cyclic
      ? { border: "2px solid #ef4444", borderRadius: 8, background: "rgba(239,68,68,0.08)", fontSize: 11 }
      : { border: "1px solid hsl(var(--border))", borderRadius: 8, background: "hsl(var(--card))", fontSize: 11 },
  }));
}

// ---------------------------------------------------------------------------
// Page
// ---------------------------------------------------------------------------

export default function GraphPage() {
  const { id } = useParams<{ id: string }>();
  const projectId = Number(id);

  const [rfNodes, setRfNodes, onNodesChange] = useNodesState<Node>([]);
  const [rfEdges, setRfEdges, onEdgesChange] = useEdgesState<Edge>([]);
  const [loading, setLoading] = useState(true);
  const [cycleCount, setCycleCount] = useState(0);
  const [nodeCount, setNodeCount] = useState(0);

  const { setOpenFile } = useProjectStore();

  useEffect(() => {
    getDependencyGraph(projectId)
      .then(({ nodes, edges, cycles }) => {
        const laid = layoutNodes(nodes, edges);
        const flowEdges: Edge[] = edges.map(e => ({
          id: e.id,
          source: e.source,
          target: e.target,
          animated: false,
          style: e.data.cyclic
            ? { stroke: "#ef4444", strokeWidth: 2 }
            : { stroke: "#888", strokeWidth: 1, opacity: 0.6 },
        }));
        setRfNodes(laid);
        setRfEdges(flowEdges);
        setCycleCount(cycles.length);
        setNodeCount(nodes.length);
      })
      .catch(() => toast.error("Failed to load dependency graph."))
      .finally(() => setLoading(false));
  }, [projectId]);

  const onNodeClick = useCallback(
    async (_: React.MouseEvent, node: Node) => {
      const path = (node.data as { path: string }).path;
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
        toast.error(`Could not open ${path}`);
      }
    },
    [projectId, setOpenFile]
  );

  if (loading) {
    return (
      <div className="h-full flex flex-col">
        {/* Stats bar skeleton */}
        <div className="shrink-0 border-b px-4 py-2 flex items-center gap-4">
          <div className="h-3 w-16 rounded bg-muted animate-pulse" />
          <div className="h-3 w-20 rounded bg-muted animate-pulse" />
        </div>
        {/* Graph area skeleton — fake nodes */}
        <div className="flex-1 relative overflow-hidden bg-muted/10">
          {[
            { top: "20%", left: "15%", w: 110 },
            { top: "20%", left: "42%", w: 90 },
            { top: "20%", left: "68%", w: 120 },
            { top: "55%", left: "28%", w: 100 },
            { top: "55%", left: "56%", w: 95 },
          ].map((s, i) => (
            <div
              key={i}
              className="absolute h-8 rounded-lg bg-muted animate-pulse"
              style={{ top: s.top, left: s.left, width: s.w }}
            />
          ))}
          <div className="absolute inset-0 flex items-center justify-center">
            <span className="text-xs text-muted-foreground flex items-center gap-1.5">
              <Loader2 size={13} className="animate-spin" />
              Building dependency graph…
            </span>
          </div>
        </div>
      </div>
    );
  }

  if (rfNodes.length === 0) {
    return (
      <div className="flex items-center justify-center h-full text-center pb-20">
        <div>
          <p className="font-medium">No dependency graph available</p>
          <p className="text-sm text-muted-foreground mt-1">
            No resolvable inter-file imports were found in this project.
          </p>
        </div>
      </div>
    );
  }

  return (
    <div className="h-full flex flex-col">
      {/* Stats bar */}
      <div className="shrink-0 border-b px-4 py-2 flex items-center gap-4 text-xs text-muted-foreground">
        <span>{nodeCount} files</span>
        <span>{rfEdges.length} imports</span>
        {cycleCount > 0 && (
          <span className="flex items-center gap-1 text-red-500 font-medium">
            <AlertTriangle size={12} />
            {cycleCount} circular {cycleCount === 1 ? "dependency" : "dependencies"} (red)
          </span>
        )}
        <span className="ml-auto">Click a node to open the file</span>
      </div>

      {/* Graph */}
      <div className="flex-1">
        <ReactFlowProvider>
          <ReactFlow
            nodes={rfNodes}
            edges={rfEdges}
            onNodesChange={onNodesChange}
            onEdgesChange={onEdgesChange}
            onNodeClick={onNodeClick}
            fitView
            fitViewOptions={{ padding: 0.2 }}
            minZoom={0.1}
            nodesDraggable
            nodesConnectable={false}
            elementsSelectable
            defaultEdgeOptions={{ type: "smoothstep" }}
          >
            <Background gap={20} size={1} />
            <Controls />
            <MiniMap
              nodeColor={n => (n.data as { cyclic?: boolean }).cyclic ? "#ef4444" : "#888"}
              maskColor="rgba(0,0,0,0.2)"
            />
          </ReactFlow>
        </ReactFlowProvider>
      </div>
    </div>
  );
}
