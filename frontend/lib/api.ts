const API_BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export interface ApiError {
  status: number;
  message: string;
}

export interface ProjectResponse {
  id: number;
  name: string;
  source_type: "github" | "zip";
  source_url: string | null;
  status: "pending" | "ingesting" | "ready" | "failed";
  ingestion_progress: number;
  current_stage_label: string | null;
  total_files: number | null;
  total_chunks: number | null;
  language_breakdown: string | null; // raw JSON string
  error_message: string | null;
  faiss_index_path: string | null;
  created_at: string;
}

export interface ProjectStatus {
  id: number;
  status: "pending" | "ingesting" | "ready" | "failed";
  ingestion_progress: number;
  current_stage_label: string | null;
  total_files: number | null;
  total_chunks: number | null;
  error_message: string | null;
}

export interface ProjectCreate {
  name: string;
  source_type: "github" | "zip";
  source_url?: string;
}

export interface FileNode {
  path: string;
  type: "file" | "directory";
  language?: string;
  line_count?: number;
  chunk_count?: number;
  children?: FileNode[];
}

export interface ConversationResponse {
  id: number;
  project_id: number;
  title: string | null;
  created_at: string;
}

export interface MessageResponse {
  id: number;
  conversation_id: number;
  role: "user" | "assistant";
  content: string;
  citations: string | null;
  model_used: string | null;
  created_at: string;
}

export interface ChunkResult {
  chunk_id: number;
  file_path: string;
  chunk_type: string;
  name: string | null;
  content: string;
  line_start: number | null;
  line_end: number | null;
  score: number;
}

// ---------------------------------------------------------------------------
// Base fetch
// ---------------------------------------------------------------------------

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const url = `${API_BASE}${path}`;
  const res = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });

  if (!res.ok) {
    let message = `HTTP ${res.status}`;
    try {
      const body = await res.json();
      message = body?.detail ?? body?.message ?? message;
    } catch {
      // ignore JSON parse errors on error responses
    }
    const err: ApiError = { status: res.status, message };
    throw err;
  }

  // 204 No Content returns no body
  if (res.status === 204) return undefined as T;

  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Project endpoints
// ---------------------------------------------------------------------------

export const getProjects = (): Promise<ProjectResponse[]> =>
  apiFetch<ProjectResponse[]>("/projects");

export const createProject = (body: ProjectCreate): Promise<ProjectResponse> =>
  apiFetch<ProjectResponse>("/projects", {
    method: "POST",
    body: JSON.stringify(body),
  });

export const deleteProject = (id: number): Promise<void> =>
  apiFetch<void>(`/projects/${id}`, { method: "DELETE" });

export const getProjectStatus = (id: number): Promise<ProjectStatus> =>
  apiFetch<ProjectStatus>(`/projects/${id}/status`);

export const triggerIngestion = (id: number): Promise<{ message: string }> =>
  apiFetch<{ message: string }>(`/projects/${id}/ingest`, { method: "POST" });

// ---------------------------------------------------------------------------
// File endpoints (used from M4 onwards — declared here for type safety)
// ---------------------------------------------------------------------------

export const getFileTree = (projectId: number): Promise<{ tree: FileNode[] }> =>
  apiFetch<{ tree: FileNode[] }>(`/projects/${projectId}/files`);

export const getFileContent = (
  projectId: number,
  filePath: string
): Promise<{ content: string; language: string; line_count: number }> =>
  apiFetch(`/projects/${projectId}/files/content?path=${encodeURIComponent(filePath)}`);

export const getLanguageBreakdown = (
  projectId: number
): Promise<{ language: string; percent: number; file_count: number }[]> =>
  apiFetch(`/projects/${projectId}/languages`);

// ---------------------------------------------------------------------------
// Chat endpoints
// ---------------------------------------------------------------------------

export const getConversations = (
  projectId: number
): Promise<ConversationResponse[]> =>
  apiFetch<ConversationResponse[]>(`/projects/${projectId}/conversations`);

export const getConversationMessages = (
  projectId: number,
  conversationId: number
): Promise<MessageResponse[]> =>
  apiFetch<MessageResponse[]>(
    `/projects/${projectId}/conversations/${conversationId}/messages`
  );

export const getChatStreamUrl = (projectId: number): string =>
  `${API_BASE}/projects/${projectId}/chat`;

// ---------------------------------------------------------------------------
// Generation endpoints
// ---------------------------------------------------------------------------

export interface ArchitectureResult {
  summary: string;
  stack: string[];
  layers: { name: string; description: string; examples: string[] }[];
}

export interface ApiEndpoint {
  method: string;
  path: string;
  handler: string;
  description: string;
}

export const getArchitecture = (projectId: number): Promise<ArchitectureResult> =>
  apiFetch<ArchitectureResult>(`/projects/${projectId}/architecture`);

export const getApiEndpoints = (projectId: number): Promise<ApiEndpoint[]> =>
  apiFetch<ApiEndpoint[]>(`/projects/${projectId}/api-endpoints`);

export const getDocstringStreamUrl = (projectId: number, chunkId: number): string =>
  `${API_BASE}/projects/${projectId}/chunks/${chunkId}/docstring`;

// ---------------------------------------------------------------------------
// Graph endpoint
// ---------------------------------------------------------------------------

export interface GraphNode {
  id: string;
  data: { label: string; path: string; language: string | null; cyclic: boolean };
  position: { x: number; y: number };
  type: string;
}

export interface GraphEdge {
  id: string;
  source: string;
  target: string;
  data: { cyclic: boolean };
  style?: Record<string, string>;
}

export interface GraphResult {
  nodes: GraphNode[];
  edges: GraphEdge[];
  cycles: string[][];
}

export const getDependencyGraph = (projectId: number): Promise<GraphResult> =>
  apiFetch<GraphResult>(`/projects/${projectId}/graph`);

// ---------------------------------------------------------------------------
// Chunk search (for doc generator function picker)
// ---------------------------------------------------------------------------

export const searchChunks = (
  projectId: number,
  query: string,
  topK = 10
): Promise<ChunkResult[]> =>
  apiFetch<ChunkResult[]>(`/projects/${projectId}/search?q=${encodeURIComponent(query)}&top_k=${topK}`);
