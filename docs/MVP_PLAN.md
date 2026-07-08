# CodeSage MVP Plan
## AI Developer Intelligence Platform — Resume MVP

**Version:** MVP 1.0
**Target Timeline:** 4 weeks (solo student developer)
**Derived from:** Full PRD v1.0 (docs/01-PRD.md through docs/10-deployment-architecture.md)

---

## 1. Final MVP Scope

CodeSage MVP is a **locally-runnable, Docker-deployed tool** that lets a developer upload any GitHub repository (by URL) or a local project (ZIP), then interact with the codebase through an AI-powered chat interface and a set of one-click analysis features.

The MVP proves the core technical thesis — that a codebase can be parsed, embedded, and queried with natural language — without any paid infrastructure. Everything runs on the developer's machine or a free-tier deployment.

**The one-sentence demo pitch:**
> "You paste a GitHub URL, and within 60 seconds you can ask the codebase any question in plain English."

---

## 2. Features Included

### Core Pipeline
- GitHub repository ingestion by URL (public repos via `git clone`)
- ZIP file upload (drag-and-drop, up to 100MB)
- File filtering (exclude `node_modules`, `.git`, binaries, lock files)
- `.gitignore`-aware file walking
- AST-level code parsing via `tree-sitter` (Python, JS, TS, Go, Java, Rust)
- Fallback text chunking for unsupported languages
- Semantic chunking (function/class/method/module level)
- Local embeddings via HuggingFace `sentence-transformers` (no API, no cost, no rate limits)
- FAISS vector index (local, file-based persistence)
- Semantic search over code chunks

### AI Features (Free Tier)
- Conversational Q&A over the codebase (multi-turn, session-scoped)
- Streaming AI responses token-by-token
- Source citations in every answer (file path + line numbers)
- Architecture summary generation
- API endpoint discovery (framework-specific pattern matching + LLM)
- Documentation generation (function-level docstrings)
- Dependency graph (import/require extraction, rendered as interactive graph)

### UI
- Project dashboard (list projects, create new, delete)
- Ingestion progress indicator (polling-based, no background workers)
- File explorer (tree view of project files)
- Code viewer (syntax highlighted, scrolls to cited line)
- Chat interface with streaming and citation links
- Dependency graph visualization (interactive, zoomable)
- One-click generation panels (architecture, API endpoints, docs)

### Infrastructure
- Fully Dockerized (`docker-compose up` starts everything)
- SQLite database (zero-config, file-based)
- No external services required except AI API keys
- `.env` file for configuration

---

## 3. Features Intentionally Excluded

The following are documented in the full PRD but are out of scope for this MVP. They are not cut because they are unimportant — they are cut to keep the build achievable in 4 weeks.

| Feature | Reason for Exclusion |
|---|---|
| User authentication / accounts | Single-user local tool; adds 1 week of auth boilerplate |
| GitHub OAuth | Single-user; public repos work with plain `git clone` |
| Email / notifications | No user accounts; no email service needed |
| Background task queue (Celery) | Ingestion runs synchronously per request; simpler for MVP |
| Redis | No sessions, no queues, no cache needed |
| PostgreSQL | SQLite is sufficient for a local single-user tool |
| Qdrant / Pinecone | Replaced by FAISS (local, zero-cost, zero-config) |
| Reranking (Cohere / cross-encoder) | Dense semantic search alone is sufficient to demonstrate the concept |
| Hybrid search (BM25 + dense) | FAISS dense search only; reduces complexity significantly |
| Rate limiting middleware | No multi-user; unnecessary for local MVP |
| Billing / Stripe | No payments |
| Subscriptions / plan tiers | No accounts |
| Multi-user collaboration | Single-user tool |
| Bug & code smell detection (LLM-based) | Requires batching many LLM calls; high API cost risk |
| Unit test generation | Deferred; not core to the demo narrative |
| Cloud deployment | Docker Compose on localhost is sufficient for interviews |
| Monitoring / Grafana / Prometheus | No production traffic to monitor |
| Sentry / error tracking | Console logging is sufficient for MVP |
| Analytics / usage tracking | No users to track |
| Export to Markdown | Can be added in 1 hour post-MVP if needed |
| Re-ingestion / diff update | Single ingest per project; re-ingest by deleting and re-uploading |
| Private GitHub repo access | Requires OAuth; public repos cover 90% of demo use cases |

---

## 4. Simplified Architecture

### Overview

```
┌──────────────────────────────────────┐
│         Browser (Next.js)            │
│                                      │
│  Dashboard │ Chat │ Graph │ Explorer │
└───────────────────┬──────────────────┘
                    │ HTTP + SSE
┌───────────────────▼──────────────────┐
│         FastAPI Backend              │
│                                      │
│  /projects   /ingest   /chat         │
│  /generate   /graph    /search       │
└─────┬──────────────────────┬─────────┘
      │                      │
┌─────▼──────┐        ┌──────▼──────┐
│  SQLite    │        │    FAISS    │
│ (metadata) │        │  (vectors,  │
│            │        │  persisted  │
│ projects   │        │  to disk)   │
│ files      │        └─────────────┘
│ chunks     │
│ messages   │
└────────────┘
      │
┌─────▼─────────────────────────────┐
│     AI Layer (Free Tier)          │
│                                   │
│  Embeddings: sentence-transformers│
│  (BAAI/bge-small-en-v1.5)         │
│  runs locally, zero API calls     │
│                                   │
│  LLM: Gemini 1.5 Flash (primary)  │
│  free: 15 RPM, 1M tokens/day      │
│                                   │
│  LLM: Groq llama-3.1-8b (fallback)│
│  free: 30 RPM, 131k context       │
└───────────────────────────────────┘
```

### Technology Stack

| Layer | Technology | Why |
|---|---|---|
| Frontend | Next.js 15, TypeScript, Tailwind CSS | SSR, streaming, type safety |
| UI components | shadcn/ui | Production-quality components, free |
| Graph visualization | React Flow | Interactive graph, MIT license |
| Code display | Monaco Editor (read-only) | VS Code's editor, free |
| Backend | FastAPI (Python 3.12) | Async, auto-docs, Python AI ecosystem |
| ORM | SQLAlchemy 2 + SQLite | Zero-config database |
| Migrations | Alembic | Schema versioning |
| Code parsing | tree-sitter | 40+ languages, production-quality |
| Token counting | tiktoken | Approximate token count for chunking |
| Embeddings | `sentence-transformers` — `BAAI/bge-small-en-v1.5` | Local, 384-d, fast on CPU, zero cost |
| Vector store | FAISS (`faiss-cpu`) | Local, persistent, no server needed |
| LLM (primary) | Google Gemini 1.5 Flash via `google-generativeai` SDK | Free tier: 15 RPM, 1M tokens/day |
| LLM (fallback) | Groq `llama-3.1-8b-instant` via `groq` SDK | Free tier: 30 RPM, triggered on Gemini 429 |
| Git operations | GitPython | Clone public repos |
| Containerization | Docker + Docker Compose | One-command startup |

### Free Tier Rate Limits (Know Before You Build)

The rate limits are real constraints to design around, not abstract concerns.

| Service | Free Limit | Design Response |
|---|---|---|
| Gemini 1.5 Flash | 15 RPM, 1M tokens/day | Catch `429`, retry after 4s, then fall to Groq |
| Groq (llama-3.1-8b) | 30 RPM | Catch `429`, retry after 2s with exponential backoff (max 3 retries) |
| HuggingFace sentence-transformers | No limit (local) | Embed in batches of 64; no throttling needed |
| FAISS | No limit (local) | No throttling needed |

**LLM fallback chain:**
```
Request → Try Gemini →
  Success → stream response
  429 / Error → Try Groq →
    Success → stream response
    429 / Error → Return "AI temporarily unavailable, retry in 30s"
```

### Data Flow (Simplified)

**Ingestion (synchronous, no worker queue):**
```
POST /ingest { repo_url or zip_file }
  → Clone / extract to temp dir
  → Walk files (filter by extension + .gitignore)
  → For each file: tree-sitter parse → extract code units
  → Chunk each unit (512 tokens max, 64 overlap)
  → Embed all chunks in batches (sentence-transformers, local)
  → Store vectors in FAISS index (persisted to disk)
  → Store metadata in SQLite
  → Update project status to READY
  → Return 200

Frontend polls GET /projects/:id/status every 2s until READY
```

**Query (RAG):**
```
POST /chat { project_id, message, conversation_id }
  → Embed question (local model)
  → FAISS top-k=8 search
  → Build prompt: system + retrieved chunks + conversation history + question
  → Call Gemini (streaming) → fallback Groq
  → SSE stream to client token-by-token
  → On completion: persist message + citations to SQLite
```

---

## 5. Simplified Database Schema

SQLite, managed with SQLAlchemy + Alembic. All IDs are integers (simpler than UUIDs for SQLite).

```sql
-- Projects
CREATE TABLE projects (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    name            TEXT NOT NULL,
    source_type     TEXT NOT NULL,         -- 'github' | 'zip'
    source_url      TEXT,                  -- GitHub URL if applicable
    status          TEXT NOT NULL DEFAULT 'pending',
                                           -- 'pending' | 'ingesting' | 'ready' | 'failed'
    ingestion_progress INTEGER DEFAULT 0,  -- 0-100
    total_files     INTEGER,
    total_chunks    INTEGER,
    language_breakdown TEXT,               -- JSON string: {"Python": 65.2}
    error_message   TEXT,
    faiss_index_path TEXT,                 -- path to .faiss file on disk
    created_at      TEXT NOT NULL          -- ISO 8601
);

-- Files within a project
CREATE TABLE project_files (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_path   TEXT NOT NULL,             -- relative path from repo root
    language    TEXT,
    line_count  INTEGER,
    chunk_count INTEGER DEFAULT 0
);

CREATE UNIQUE INDEX idx_project_files ON project_files(project_id, file_path);

-- Code chunks (metadata for FAISS vectors)
CREATE TABLE project_chunks (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id      INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    file_id         INTEGER NOT NULL REFERENCES project_files(id) ON DELETE CASCADE,
    faiss_index     INTEGER NOT NULL,      -- position in the FAISS index
    chunk_type      TEXT NOT NULL,         -- 'function' | 'class' | 'method' | 'module' | 'block'
    name            TEXT,
    content         TEXT NOT NULL,
    line_start      INTEGER,
    line_end        INTEGER,
    token_count     INTEGER
);

CREATE INDEX idx_chunks_project ON project_chunks(project_id);
CREATE INDEX idx_chunks_faiss ON project_chunks(project_id, faiss_index);

-- Conversations (chat sessions)
CREATE TABLE conversations (
    id          INTEGER PRIMARY KEY AUTOINCREMENT,
    project_id  INTEGER NOT NULL REFERENCES projects(id) ON DELETE CASCADE,
    title       TEXT,                      -- first user message, truncated
    created_at  TEXT NOT NULL
);

-- Messages within a conversation
CREATE TABLE messages (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    conversation_id INTEGER NOT NULL REFERENCES conversations(id) ON DELETE CASCADE,
    role            TEXT NOT NULL,         -- 'user' | 'assistant'
    content         TEXT NOT NULL,
    citations       TEXT,                  -- JSON: [{"file":"...","line_start":42,"line_end":67}]
    model_used      TEXT,                  -- 'gemini-1.5-flash' | 'groq/llama-3.1-8b-instant'
    created_at      TEXT NOT NULL
);

CREATE INDEX idx_messages_conv ON messages(conversation_id);
```

**FAISS index storage:**
Each project gets one FAISS index file stored at `data/faiss/{project_id}.faiss` alongside a companion `data/faiss/{project_id}.meta.json` (chunk ID mapping). Both are gitignored. The `faiss_index_path` column in `projects` stores this path.

---

## 6. Folder Structure

```
codesage-mvp/
│
├── backend/
│   ├── app/
│   │   ├── main.py                  # FastAPI app, route registration, CORS
│   │   ├── database.py              # SQLAlchemy engine + session (SQLite)
│   │   ├── models.py                # All SQLAlchemy models
│   │   ├── schemas.py               # All Pydantic request/response schemas
│   │   │
│   │   ├── ingestion/
│   │   │   ├── router.py            # POST /ingest, GET /projects/:id/status
│   │   │   ├── pipeline.py          # Orchestrates all ingestion stages
│   │   │   ├── git_ingestion.py     # git clone via GitPython
│   │   │   ├── zip_ingestion.py     # ZIP extraction with zip-slip protection
│   │   │   ├── file_walker.py       # Walk + filter files
│   │   │   ├── ast_parser.py        # tree-sitter extraction
│   │   │   ├── chunker.py           # 512-token chunking with overlap
│   │   │   └── embedder.py          # sentence-transformers batch embed + FAISS
│   │   │
│   │   ├── search/
│   │   │   ├── router.py            # GET /search (optional standalone endpoint)
│   │   │   └── service.py           # FAISS load + query + return top-k chunks
│   │   │
│   │   ├── chat/
│   │   │   ├── router.py            # POST /projects/:id/chat (SSE stream)
│   │   │   ├── service.py           # RAG orchestration: search → prompt → LLM
│   │   │   ├── prompt_builder.py    # System prompt + context + history assembly
│   │   │   └── llm_client.py        # Gemini primary + Groq fallback, rate limit handling
│   │   │
│   │   ├── generation/
│   │   │   ├── router.py            # GET /projects/:id/architecture, /api-endpoints, /generate/docs
│   │   │   ├── architecture.py      # Architecture summary via LLM
│   │   │   ├── api_scanner.py       # Regex + LLM endpoint detection
│   │   │   └── doc_generator.py     # Docstring generation for a function
│   │   │
│   │   ├── graph/
│   │   │   ├── router.py            # GET /projects/:id/graph
│   │   │   ├── builder.py           # Import/require parsing → adjacency list
│   │   │   └── cycle_detector.py    # Tarjan's SCC for circular dependency detection
│   │   │
│   │   └── projects/
│   │       └── router.py            # GET/POST/DELETE /projects
│   │
│   ├── data/                        # Gitignored runtime data
│   │   ├── codesage.db              # SQLite database file
│   │   ├── faiss/                   # FAISS index files per project
│   │   └── uploads/                 # Temp storage for ZIP files
│   │
│   ├── tests/
│   │   ├── test_ast_parser.py
│   │   ├── test_chunker.py
│   │   ├── test_search.py
│   │   └── test_ingestion_pipeline.py
│   │
│   ├── migrations/                  # Alembic versioned migrations
│   │   └── versions/
│   │
│   ├── requirements.txt
│   ├── alembic.ini
│   ├── .env.example
│   └── Dockerfile
│
├── frontend/
│   ├── src/
│   │   ├── app/
│   │   │   ├── layout.tsx
│   │   │   ├── page.tsx             # Landing / redirect to /dashboard
│   │   │   ├── dashboard/
│   │   │   │   └── page.tsx         # Project list + create new
│   │   │   └── projects/
│   │   │       └── [id]/
│   │   │           ├── layout.tsx   # Project shell: sidebar file tree + topnav
│   │   │           ├── page.tsx     # Project overview / status
│   │   │           ├── chat/
│   │   │           │   └── page.tsx
│   │   │           ├── graph/
│   │   │           │   └── page.tsx
│   │   │           └── generate/
│   │   │               └── page.tsx # Architecture + API endpoints + docs
│   │   │
│   │   ├── components/
│   │   │   ├── ui/                  # shadcn/ui primitives
│   │   │   ├── ChatInterface.tsx    # Messages + streaming + citations
│   │   │   ├── FileExplorer.tsx     # Tree view of project files
│   │   │   ├── CodeViewer.tsx       # Monaco editor, read-only, jump-to-line
│   │   │   ├── DependencyGraph.tsx  # React Flow wrapper
│   │   │   ├── IngestionProgress.tsx
│   │   │   └── ProjectCard.tsx
│   │   │
│   │   └── lib/
│   │       ├── api.ts               # Typed fetch wrapper
│   │       └── streaming.ts         # SSE consumer for chat
│   │
│   ├── next.config.ts
│   ├── package.json
│   └── Dockerfile
│
├── docker-compose.yml               # Starts backend + frontend together
├── .env.example                     # Template for GEMINI_API_KEY, GROQ_API_KEY
├── Makefile                         # make dev, make test, make build
└── README.md
```

---

## 7. Milestones

### Milestone 1 — Foundation (Days 1–4)
**Goal:** The project runs locally. You can create a project, trigger ingestion from a GitHub URL or ZIP, and see files appear in the database.

**Tasks:**
- Scaffold monorepo: `backend/` with FastAPI, `frontend/` with Next.js
- Set up SQLite + SQLAlchemy models + Alembic
- `docker-compose.yml` that starts both services
- `GET /projects`, `POST /projects`, `DELETE /projects/:id`
- Ingestion endpoint: clone GitHub repo (shallow) or extract ZIP to temp dir
- File walker: extension whitelist, `.gitignore` respect, size filter
- Project status polling: `GET /projects/:id/status`
- Frontend: project dashboard — list, create (input GitHub URL or upload ZIP), delete

**Acceptance Criteria:**
- [ ] `docker-compose up` starts both services with no manual steps
- [ ] Submitting `https://github.com/expressjs/express` creates a project and clones the repo
- [ ] File walker output (file list with paths and languages) is visible in the API response
- [ ] Project status cycles from `pending` → `ingesting` → `ready` (or `failed` with an error message)
- [ ] Frontend shows project cards with status badges
- [ ] All backend endpoints are documented at `http://localhost:8000/docs`

---

### Milestone 2 — AST Parsing + Embeddings + FAISS (Days 5–9)
**Goal:** The codebase is fully parsed, chunked, embedded, and stored in a searchable FAISS index.

**Tasks:**
- Integrate `tree-sitter` with language grammars for Python, JS/TS, Go, Java
- `ASTParser` class: extract functions, classes, methods, module headers
- `Chunker`: 512-token max, 64-token overlap, context prefix for sub-chunks
- `Embedder`: load `BAAI/bge-small-en-v1.5` via `sentence-transformers`, batch embed (size 64)
- FAISS index creation, upsert, persistence to disk
- Metadata persistence: `project_files` + `project_chunks` tables populated
- Fallback text chunker for unsupported languages
- Full ingestion pipeline: wire all stages together in `pipeline.py`
- Unit tests: parser, chunker, embedder with small fixture files

**Acceptance Criteria:**
- [ ] Ingesting a 50-file Python project produces > 100 chunks in the database
- [ ] Each chunk record has `file_path`, `chunk_type`, `name`, `line_start`, `line_end`
- [ ] FAISS index file exists on disk after ingestion
- [ ] `search/service.py`: given a query string, returns top-8 chunks with metadata
- [ ] Embedding a single sentence takes < 500ms on CPU (no GPU required)
- [ ] Unit tests for parser, chunker, and searcher pass

---

### Milestone 3 — AI Chat (Days 10–14)
**Goal:** A developer can have a multi-turn conversation about the codebase with streaming responses and source citations.

**Tasks:**
- `llm_client.py`: Gemini 1.5 Flash (primary, streaming), Groq fallback (streaming)
- Rate limit handling: catch `429`, wait, retry, then fall back
- `prompt_builder.py`: system prompt + retrieved chunks + last 6 conversation turns + question
- `POST /projects/:id/chat` SSE endpoint: stream tokens to client
- Conversations + messages persisted to SQLite
- `GET /projects/:id/conversations` — list sessions
- `GET /projects/:id/conversations/:id` — full history
- Frontend: full chat UI — message bubbles, streaming indicator, conversation list
- Citation display: `[file: src/auth.py, lines: 42-67]` renders as a clickable link
- Citation link opens CodeViewer scrolled to that line

**Acceptance Criteria:**
- [ ] Asking "How does authentication work?" on an auth-containing project returns a cited answer
- [ ] Streaming works: tokens appear one-by-one, not all at once
- [ ] Every assistant response contains at least one file citation
- [ ] Conversation history is maintained: a follow-up question ("give me an example") has context
- [ ] Gemini 429 error triggers Groq fallback without the user seeing an error
- [ ] Chat works correctly on three different test repos

---

### Milestone 4 — File Explorer + Code Viewer (Days 15–17)
**Goal:** The codebase is navigable. Clicking a citation jumps to the right file and line.

**Tasks:**
- `GET /projects/:id/files` — return full file tree as nested JSON
- `GET /projects/:id/files/content?path=src/auth.py` — return raw file content
- Frontend: `FileExplorer.tsx` — collapsible tree with language icons
- Frontend: `CodeViewer.tsx` — Monaco editor in read-only mode, syntax highlighting, `scrollToLine(n)`
- Citation links in chat wire to CodeViewer navigation
- File click in explorer opens that file in CodeViewer
- Language stat bar (shows breakdown: Python 65%, JS 35%)

**Acceptance Criteria:**
- [ ] File tree renders correctly for projects with nested directories
- [ ] Clicking a file in the explorer opens it in the code viewer
- [ ] Clicking a citation in chat scrolls the code viewer to the correct line with the line highlighted
- [ ] Code viewer shows correct syntax highlighting for Python, JS, TS, Go
- [ ] Language breakdown display is accurate

---

### Milestone 5 — Generation Features (Days 18–22)
**Goal:** One-click architectural intelligence — the three features that make this stand out in an interview.

**Tasks:**

**Architecture Summary:**
- Retrieve top-level config files (package.json, requirements.txt, go.mod, Dockerfile) + README
- Sample 3 files from each major directory
- LLM call: summarize tech stack, layers, major subsystems
- Return structured JSON: `{ summary, stack, layers }`

**API Endpoint Discovery:**
- Framework-agnostic regex patterns (Express router, FastAPI decorators, Django urlpatterns, Spring @GetMapping)
- Run patterns over all chunks, collect matches
- LLM call to extract method, path, handler, description from matched chunks
- Return deduplicated, sorted list of endpoints

**Documentation Generation:**
- User selects a function from the file explorer
- Retrieve the function's chunk from SQLite
- Prompt LLM: "Generate a [language] docstring for this function"
- Stream the result back; display with copy button
- Support Python (Google-style), JS/TS (JSDoc)

**Dependency Graph:**
- Import/require extraction: regex patterns per language (Python `import`, JS `require`/`import`, Go `import`)
- Build adjacency list: `{ source_file: [imported_file, ...] }`
- Cycle detection via DFS
- `GET /projects/:id/graph` returns nodes + edges + circular dep flags
- Frontend: React Flow graph — click node to open file, circular deps highlighted in red

**Acceptance Criteria:**
- [ ] Architecture summary correctly identifies the framework and major layers for Flask, Express, and FastAPI sample projects
- [ ] API endpoint scanner finds > 80% of routes in a known Express/FastAPI project
- [ ] Docstring generation returns a valid, language-appropriate docstring for a given function
- [ ] Dependency graph renders with > 20 nodes for a mid-size project without crashing
- [ ] Circular dependencies (if any) are visually highlighted in red

---

### Milestone 6 — Docker Deployment + Polish (Days 23–28)
**Goal:** The project works out of the box for anyone who clones the repo. Demo-ready.

**Tasks:**
- Production Dockerfiles for backend and frontend
- `docker-compose.yml`: volume-mount `data/` so SQLite and FAISS persist between restarts
- `.env.example` with `GEMINI_API_KEY` and `GROQ_API_KEY` as the only required config
- `README.md`: setup instructions (3 steps: clone → add `.env` → `docker-compose up`)
- Error handling: ingestion failure shows a human-readable message in the UI
- Empty states: good-looking placeholders when project has no conversations yet
- Loading skeletons for file tree and graph
- Ingestion progress bar with current stage label ("Parsing files...", "Generating embeddings...")
- Test the full flow end-to-end on 3 diverse repos (Python/FastAPI, Node/Express, Java/Spring)
- Write `tests/e2e/` smoke test: ingest a small repo, ask a question, verify citation returned

**Acceptance Criteria:**
- [ ] `git clone` + `cp .env.example .env` (add API keys) + `docker-compose up` → fully working app in under 5 minutes
- [ ] All data persists across `docker-compose down` + `docker-compose up` (volume mounts work)
- [ ] End-to-end flow tested on: `fastapi/fastapi`, `expressjs/express`, one Java repo
- [ ] The app has no visible error states on happy paths for these three repos
- [ ] README is clear enough for a non-developer to set up the project

---

## 8. Development Order

The milestones above define the order. Rationale:

1. **Foundation first** — Nothing else is buildable without the project model and Docker setup.
2. **Pipeline before UI** — The AI features are the core; the UI wraps them. Validate the pipeline works (via `/docs` Swagger UI) before building React components.
3. **Chat before generation** — Chat validates the full RAG stack. Generation features reuse the LLM client and search service built in Milestone 3.
4. **File explorer after chat** — Citations are only useful if the file explorer exists to navigate to them.
5. **Docker last** — Polish and containerize a working app, not a broken one.

Do not build the frontend and backend in parallel for the same feature. Build the backend endpoint first, test it in Swagger UI, then build the frontend for it. This avoids the "both sides are broken" debugging trap.

---

## 9. Estimated Implementation Time

| Milestone | Days | Effort Level |
|---|---|---|
| 1 — Foundation | 4 | Medium (setup-heavy, but no novel problems) |
| 2 — Parsing + Embeddings + FAISS | 5 | High (tree-sitter integration is the hardest technical problem) |
| 3 — AI Chat | 5 | High (streaming SSE + fallback LLM client requires care) |
| 4 — File Explorer + Code Viewer | 3 | Medium (Monaco integration is documented) |
| 5 — Generation Features | 5 | Medium-High (4 separate features, mostly prompt engineering) |
| 6 — Docker + Polish | 6 | Medium (Docker setup + debugging + demo prep) |
| **Total** | **28 days** | |

**Buffer:** 2 days are implicit in the 4-week window for debugging and unexpected blockers. Do not use them unless you are blocked.

**Most likely delay:** Milestone 2 (tree-sitter Python bindings + language grammars have non-obvious setup). Plan to spend the first half of Day 5 on environment setup alone.

---

## 10. Acceptance Criteria Summary (Interview Readiness)

The project is interview-ready when you can demonstrate this flow live, without preparation, in under 10 minutes:

```
1. Open the app at http://localhost:3000
2. Paste a GitHub URL (use a real open-source repo the interviewer recognizes)
3. Watch the ingestion progress bar complete
4. Navigate the file explorer
5. Ask: "What does this project do?"          → cited answer
6. Ask: "How does authentication work here?"  → cited flow explanation
7. Click a citation → code viewer jumps to exact line
8. Click "Architecture Summary"               → tech stack + layers displayed
9. Click "API Endpoints"                      → list of discovered routes
10. Click "Dependency Graph"                  → interactive graph rendered
```

These 10 steps prove: parsing, embedding, search, RAG, streaming, citation linking, and three different generation capabilities — all in one demo.

### Per-Milestone Acceptance Summary

| Milestone | Done When |
|---|---|
| 1 | Ingestion completes and project status reaches READY |
| 2 | FAISS search returns correct top-8 chunks for a sample query |
| 3 | Streaming chat returns cited answer; Groq fallback works |
| 4 | Citation click jumps to correct line in Monaco editor |
| 5 | All three generation features return correct output on known repos |
| 6 | `docker-compose up` works on a fresh machine with only `.env` configured |
