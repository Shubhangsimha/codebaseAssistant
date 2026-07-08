# Implementation Backlog
## CodeSage MVP — Sprint-Ready Task Breakdown

**Version:** 1.0
**Source:** MVP_PLAN.md
**Total Tasks:** 96
**Estimated Total Time:** ~55–65 hours of focused work

---

## How to Read This Document

- **Task ID** format: `M{milestone}-T{number}` (e.g., M1-T03)
- **Dependencies** list Task IDs that must be complete before starting
- Tasks within a milestone are ordered by dependency — work top to bottom
- `[BE]` = backend-only task, `[FE]` = frontend-only, `[INFRA]` = config/tooling
- Do not skip tasks; each one has a downstream dependent

---

## Milestone 1 — Foundation
**Goal:** Both services start via `docker-compose up`. Projects can be created, ingestion acquires source code, and the dashboard renders.

---

### M1-T01 — Scaffold backend directory structure `[BE]`
- **Description:** Create the `backend/` directory tree exactly as specified in MVP_PLAN.md section 6. Create all `__init__.py` files and empty module placeholders so Python can import them. Create `requirements.txt` with pinned versions for FastAPI, SQLAlchemy, Alembic, pydantic, uvicorn, python-multipart, python-dotenv.
- **Files to create:** `backend/app/__init__.py`, `backend/app/main.py` (stub), `backend/app/database.py` (stub), `backend/app/models.py` (stub), `backend/app/schemas.py` (stub), all module `__init__.py` files, `backend/requirements.txt`
- **Dependencies:** None
- **Acceptance Criteria:** `cd backend && pip install -r requirements.txt && python -c "from app import main"` exits 0
- **Estimated Time:** 20 min

---

### M1-T02 — FastAPI app factory with CORS and health check `[BE]`
- **Description:** Implement `app/main.py`. Create the FastAPI app instance, add `CORSMiddleware` allowing `http://localhost:3000`, register a `GET /health` route returning `{"status": "ok"}`, and add a startup log message. Do not register feature routers yet — just the skeleton.
- **Files to modify:** `backend/app/main.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** `uvicorn app.main:app --reload` starts without errors. `GET /health` returns `{"status": "ok"}`. Swagger UI is accessible at `http://localhost:8000/docs`.
- **Estimated Time:** 20 min

---

### M1-T03 — SQLAlchemy async engine + session factory `[BE]`
- **Description:** Implement `database.py`. Create a SQLAlchemy `AsyncEngine` pointing at `sqlite+aiosqlite:///./data/codesage.db`. Define the `Base` declarative class, the `AsyncSessionLocal` factory, and a `get_db` async generator FastAPI dependency. Ensure the `data/` directory is created on startup if it does not exist.
- **Files to modify:** `backend/app/database.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** Importing `from app.database import get_db, Base` works without error. The `data/` directory is auto-created when the app starts.
- **Estimated Time:** 20 min

---

### M1-T04 — SQLAlchemy models `[BE]`
- **Description:** Implement all five SQLAlchemy ORM models in `models.py` matching the schema in MVP_PLAN.md section 5 exactly: `Project`, `ProjectFile`, `ProjectChunk`, `Conversation`, `Message`. Use `INTEGER` primary keys, `TEXT` columns for strings/JSON, and cascade `ON DELETE CASCADE` on all foreign keys. Import `Base` from `database.py`.
- **Files to modify:** `backend/app/models.py`
- **Dependencies:** M1-T03
- **Acceptance Criteria:** `from app.models import Project, ProjectFile, ProjectChunk, Conversation, Message` imports without error. All five classes have the correct columns as per the schema.
- **Estimated Time:** 30 min

---

### M1-T05 — Alembic setup + initial migration `[BE]`
- **Description:** Run `alembic init migrations` inside `backend/`. Configure `alembic.ini` to use the SQLite URL. Edit `migrations/env.py` to import `Base` from `app.models` and set `target_metadata = Base.metadata`. Generate the first migration with `alembic revision --autogenerate -m "initial_schema"`. Verify the generated file creates all 5 tables.
- **Files to create/modify:** `backend/alembic.ini`, `backend/migrations/env.py`, `backend/migrations/versions/0001_initial_schema.py`
- **Dependencies:** M1-T04
- **Acceptance Criteria:** `alembic upgrade head` runs without error and creates `data/codesage.db` with all 5 tables verifiable via `sqlite3 data/codesage.db .tables`.
- **Estimated Time:** 25 min

---

### M1-T06 — Pydantic schemas for projects `[BE]`
- **Description:** Implement `schemas.py`. Define: `ProjectCreate` (name, source_type, source_url optional), `ProjectResponse` (all fields from the Project model), `ProjectStatus` (id, status, ingestion_progress, total_files, total_chunks, error_message), `FileNode` (path, type: file/directory, language optional, children optional). These are the request/response contracts for the projects and ingestion routes.
- **Files to modify:** `backend/app/schemas.py`
- **Dependencies:** M1-T04
- **Acceptance Criteria:** All schema classes can be instantiated with valid data and serialized to JSON. `ProjectCreate(name="test", source_type="github", source_url="https://...")` works without error.
- **Estimated Time:** 20 min

---

### M1-T07 — Projects router (CRUD) `[BE]`
- **Description:** Implement `projects/router.py`. Define three endpoints: `GET /projects` returns all projects sorted by `created_at DESC`; `POST /projects` creates a project with status `pending` and returns the `ProjectResponse`; `DELETE /projects/{project_id}` deletes the project record (cascade handles children) and removes the FAISS index file from disk if it exists. Register this router on `app/main.py` with prefix `/projects`.
- **Files to create/modify:** `backend/app/projects/router.py`, `backend/app/main.py`
- **Dependencies:** M1-T05, M1-T06
- **Acceptance Criteria:** All three endpoints appear in Swagger UI. `POST /projects` with a valid body returns 201 with an ID. `DELETE /projects/1` returns 204. `GET /projects` returns a list.
- **Estimated Time:** 30 min

---

### M1-T08 — Git ingestion module `[BE]`
- **Description:** Implement `ingestion/git_ingestion.py`. Define `clone_repository(repo_url: str, dest_dir: Path) -> Path`. Use `GitPython`'s `Repo.clone_from` with `depth=1` (shallow clone) and `single_branch=True`. Validate that the URL is a GitHub URL before cloning. Return the path to the cloned directory. Raise a descriptive `ValueError` if the clone fails.
- **Files to create:** `backend/app/ingestion/git_ingestion.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** Calling `clone_repository("https://github.com/tiangolo/fastapi", Path("/tmp/test"))` succeeds and returns a path containing a `README.md`. Passing an invalid URL raises `ValueError`.
- **Estimated Time:** 25 min

---

### M1-T09 — ZIP ingestion module `[BE]`
- **Description:** Implement `ingestion/zip_ingestion.py`. Define `extract_zip(zip_path: Path, dest_dir: Path) -> Path`. Use Python's `zipfile` module. Before extracting each member, resolve its destination path and assert it starts with `dest_dir` (zip-slip protection). If the archive has a single top-level directory, return that directory as the root; otherwise return `dest_dir`. Raise `ValueError` on zip-slip attempts.
- **Files to create:** `backend/app/ingestion/zip_ingestion.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** A valid ZIP extracts correctly. A ZIP with a path traversal entry (e.g., `../../etc/passwd`) raises `ValueError` before any file is written.
- **Estimated Time:** 25 min

---

### M1-T10 — File walker `[BE]`
- **Description:** Implement `ingestion/file_walker.py`. Define `walk_files(root: Path) -> list[dict]` that returns a list of `{path, relative_path, language, size_bytes}` dicts. Apply: (1) extension whitelist (py, js, ts, tsx, jsx, go, java, rs, c, cpp, cs, rb, php, md, yaml, yml, toml, sql, sh); (2) skip directories in `EXCLUDED_DIRS` (node_modules, .git, dist, build, __pycache__, venv, .next, target, vendor); (3) skip files > 200KB; (4) parse `.gitignore` at repo root using `pathspec` library and filter matches.
- **Files to create:** `backend/app/ingestion/file_walker.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** Walking a cloned `fastapi/fastapi` repo returns only `.py` and `.md` files. `node_modules/` content is never returned. Files larger than 200KB are excluded. A `.gitignore`-excluded pattern is respected.
- **Estimated Time:** 30 min

---

### M1-T11 — Ingestion pipeline — stages 1 & 2 `[BE]`
- **Description:** Implement `ingestion/pipeline.py`. Define `run_ingestion(project_id: int, db: AsyncSession)` as an async function. It should: (1) set project status to `ingesting`, (2) call git or zip acquisition based on `source_type`, (3) call `walk_files`, (4) persist `ProjectFile` records for each discovered file, (5) update `project.total_files` and `project.status = "ready"` (or `"failed"` with `error_message` on exception). Store the cloned/extracted root path on the project record (add a `repo_path` TEXT column via a new Alembic migration). This is the full pipeline for Milestone 1 — AST and embedding stages are added in Milestone 2.
- **Files to create/modify:** `backend/app/ingestion/pipeline.py`, new Alembic migration for `repo_path` column
- **Dependencies:** M1-T07, M1-T08, M1-T09, M1-T10
- **Acceptance Criteria:** Calling `run_ingestion` on a GitHub project clones the repo, populates `project_files`, and sets status to `ready`. On a bad URL it sets status to `failed` with a message.
- **Estimated Time:** 35 min

---

### M1-T12 — Ingestion router + status endpoint `[BE]`
- **Description:** Implement `ingestion/router.py`. Define `POST /projects/{project_id}/ingest` which calls `run_ingestion` directly (synchronous for MVP — no background workers). Define `GET /projects/{project_id}/status` which returns `ProjectStatus`. Register both routes in `app/main.py`. Add a `404` guard: raise `HTTPException(404)` if the project does not belong to the known projects.
- **Files to create/modify:** `backend/app/ingestion/router.py`, `backend/app/main.py`
- **Dependencies:** M1-T07, M1-T11
- **Acceptance Criteria:** `POST /projects/1/ingest` triggers ingestion and returns 200 when done. `GET /projects/1/status` returns `{ "status": "ready", "ingestion_progress": 100 }` after ingestion. Returns 404 for unknown project IDs.
- **Estimated Time:** 25 min

---

### M1-T13 — Backend `.env` loading + config `[BE]`
- **Description:** Create `backend/.env.example` with `GEMINI_API_KEY=`, `GROQ_API_KEY=`, `DATA_DIR=./data`. Create `backend/app/config.py` using `pydantic-settings` `BaseSettings` that reads from the `.env` file. Import and use `settings.DATA_DIR` in `database.py` and `pipeline.py` so the data directory is configurable.
- **Files to create/modify:** `backend/.env.example`, `backend/app/config.py`, `backend/app/database.py`
- **Dependencies:** M1-T03
- **Acceptance Criteria:** Renaming `.env.example` to `.env` and starting the app reads the correct values. Missing required env vars (API keys) log a warning but do not crash startup.
- **Estimated Time:** 20 min

---

### M1-T14 — Scaffold frontend `[FE]`
- **Description:** Create the Next.js 15 frontend using `npx create-next-app@latest frontend --typescript --tailwind --app --no-src-dir`. Then install: `shadcn` (init with default config), `@tanstack/react-query`, `zustand`, `lucide-react`. Create the directory structure from MVP_PLAN.md section 6 for the frontend. Remove the default `page.tsx` content.
- **Files to create:** `frontend/` — full scaffold per folder structure
- **Dependencies:** None (can run in parallel with M1-T01 through M1-T13)
- **Acceptance Criteria:** `cd frontend && npm run dev` starts on port 3000 with no TypeScript errors. The default Next.js page is accessible.
- **Estimated Time:** 20 min

---

### M1-T15 — Frontend API client `[FE]`
- **Description:** Implement `frontend/src/lib/api.ts`. Create a base `apiFetch<T>(path, options?)` function that: prepends `http://localhost:8000` (from `NEXT_PUBLIC_API_URL` env var), sets `Content-Type: application/json`, and throws a typed `ApiError` with `{ status, code, message }` on non-2xx responses. Export typed helper functions: `getProjects()`, `createProject(body)`, `deleteProject(id)`, `getProjectStatus(id)`, `triggerIngestion(id)`. Add `frontend/.env.local` with `NEXT_PUBLIC_API_URL=http://localhost:8000`.
- **Files to create:** `frontend/src/lib/api.ts`, `frontend/.env.local`
- **Dependencies:** M1-T14
- **Acceptance Criteria:** TypeScript compiles without errors. `getProjects()` can be called from a component and returns typed data.
- **Estimated Time:** 25 min

---

### M1-T16 — ProjectCard component `[FE]`
- **Description:** Create `frontend/src/components/ProjectCard.tsx`. Render a card showing: project name, status badge (color-coded: grey=pending, yellow=ingesting, green=ready, red=failed), total files count, creation date, and a Delete button. Accept `project: ProjectResponse` and `onDelete: (id) => void` as props. Use shadcn `Card`, `Badge`, and `Button` primitives.
- **Files to create:** `frontend/src/components/ProjectCard.tsx`
- **Dependencies:** M1-T14, M1-T15
- **Acceptance Criteria:** Component renders correctly in isolation with mock data. Status badge shows the correct color for each status value. Delete button calls `onDelete`.
- **Estimated Time:** 25 min

---

### M1-T17 — CreateProjectModal component `[FE]`
- **Description:** Create `frontend/src/components/CreateProjectModal.tsx`. Render a shadcn `Dialog` with a tab selector: "GitHub URL" and "ZIP Upload". GitHub tab: text input for URL with basic URL validation. ZIP tab: file drag-and-drop input (accept `.zip`, max 100MB enforced on client). Both tabs have a "Create Project" button that calls the appropriate API and closes the modal on success.
- **Files to create:** `frontend/src/components/CreateProjectModal.tsx`
- **Dependencies:** M1-T15, M1-T16
- **Acceptance Criteria:** Modal opens and closes correctly. GitHub URL tab validates that input starts with `https://github.com`. ZIP tab accepts `.zip` files only. Submitting calls `createProject()` from the API client.
- **Estimated Time:** 35 min

---

### M1-T18 — IngestionProgress component `[FE]`
- **Description:** Create `frontend/src/components/IngestionProgress.tsx`. Accept `projectId: number` as a prop. On mount, poll `GET /projects/:id/status` every 2 seconds using `setInterval`. Display a progress bar (shadcn `Progress`) and the current stage text. When status is `ready` or `failed`, stop polling and call an `onComplete(status)` callback prop.
- **Files to create:** `frontend/src/components/IngestionProgress.tsx`
- **Dependencies:** M1-T15
- **Acceptance Criteria:** Component polls the status endpoint while status is `pending` or `ingesting`. Polling stops when status reaches a terminal state. Progress bar reflects `ingestion_progress` 0–100.
- **Estimated Time:** 25 min

---

### M1-T19 — Dashboard page `[FE]`
- **Description:** Implement `frontend/src/app/dashboard/page.tsx`. Fetch and render the project list using `getProjects()`. Show a "New Project" button that opens `CreateProjectModal`. Render one `ProjectCard` per project. After creating a project, immediately trigger `POST /projects/:id/ingest` and show `IngestionProgress` inline on the card. Clicking a ready project navigates to `/projects/[id]`. Root `page.tsx` should redirect to `/dashboard`.
- **Files to create/modify:** `frontend/src/app/dashboard/page.tsx`, `frontend/src/app/page.tsx`
- **Dependencies:** M1-T16, M1-T17, M1-T18
- **Acceptance Criteria:** Dashboard loads and shows existing projects. Creating a new project via GitHub URL shows the progress bar. After completion, the card shows status `ready`. Navigating to `/dashboard` is the app entry point.
- **Estimated Time:** 30 min

---

### M1-T20 — Backend Dockerfile `[INFRA]`
- **Description:** Create `backend/Dockerfile`. Use `python:3.12-slim` as base. Copy `requirements.txt`, run `pip install --no-cache-dir`. Copy the `app/` and `migrations/` directories. Set `WORKDIR /app`. The `CMD` should run `alembic upgrade head && uvicorn app.main:app --host 0.0.0.0 --port 8000`. Expose port 8000. Create `backend/.dockerignore` excluding `.git`, `data/`, `__pycache__`, `*.pyc`.
- **Files to create:** `backend/Dockerfile`, `backend/.dockerignore`
- **Dependencies:** M1-T02, M1-T05
- **Acceptance Criteria:** `docker build -t codesage-api ./backend` completes without errors. Running the image and hitting `/health` returns 200.
- **Estimated Time:** 20 min

---

### M1-T21 — Frontend Dockerfile `[INFRA]`
- **Description:** Create `frontend/Dockerfile` using a multi-stage build: stage 1 (`node:20-alpine` as builder) installs deps and runs `next build`; stage 2 (`node:20-alpine`) copies the build output and runs `next start`. Create `frontend/.dockerignore` excluding `.git`, `node_modules`, `.next`. Expose port 3000.
- **Files to create:** `frontend/Dockerfile`, `frontend/.dockerignore`
- **Dependencies:** M1-T14
- **Acceptance Criteria:** `docker build -t codesage-web ./frontend` completes without errors. Running the image serves the dashboard on port 3000.
- **Estimated Time:** 20 min

---

### M1-T22 — `docker-compose.yml` + Makefile `[INFRA]`
- **Description:** Create the root `docker-compose.yml` with two services: `api` (builds from `./backend`, ports `8000:8000`, mounts `./backend/data:/app/data` volume, loads `env_file: .env`) and `web` (builds from `./frontend`, ports `3000:3000`, environment `NEXT_PUBLIC_API_URL=http://api:8000`). Create root `.env.example` with `GEMINI_API_KEY=` and `GROQ_API_KEY=`. Create `Makefile` with targets: `dev` (docker-compose up), `build` (docker-compose build), `test` (pytest in backend container), `down` (docker-compose down).
- **Files to create:** `docker-compose.yml`, `.env.example`, `Makefile`
- **Dependencies:** M1-T20, M1-T21
- **Acceptance Criteria:** `docker-compose up` starts both services. The frontend at `localhost:3000` can reach the API at `localhost:8000`. The `data/` volume persists after `docker-compose down && docker-compose up`.
- **Estimated Time:** 25 min

---

## Milestone 2 — AST Parsing + Embeddings + FAISS
**Goal:** Ingestion runs the full pipeline. Chunks are stored in FAISS and SQLite and are searchable by semantic query.

---

### M2-T01 — Install and verify tree-sitter + grammars `[BE]`
- **Description:** Add to `requirements.txt`: `tree-sitter`, `tree-sitter-python`, `tree-sitter-javascript`, `tree-sitter-typescript`, `tree-sitter-go`, `tree-sitter-java`, `tree-sitter-rust`. Create `ingestion/languages/__init__.py` that imports each language grammar and builds a `LANGUAGE_MAP: dict[str, Language]` keyed by file extension. Verify each grammar loads correctly with a small parse test.
- **Files to create/modify:** `requirements.txt`, `backend/app/ingestion/languages/__init__.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** `from app.ingestion.languages import LANGUAGE_MAP` imports without error. `LANGUAGE_MAP[".py"]` is a valid `Language` object. `LANGUAGE_MAP[".ts"]` works for TypeScript.
- **Estimated Time:** 25 min

---

### M2-T02 — CodeUnit dataclass + ChunkType enum `[BE]`
- **Description:** Define in `ingestion/ast_parser.py` (top of file): a `ChunkType` string enum with values `FUNCTION`, `CLASS`, `METHOD`, `MODULE`, `BLOCK`; a `CodeUnit` dataclass with fields `file_path: str`, `language: str`, `chunk_type: ChunkType`, `name: str | None`, `content: str`, `line_start: int`, `line_end: int`, `parent_name: str | None`. These are the contracts between parser and chunker.
- **Files to create:** `backend/app/ingestion/ast_parser.py` (partial)
- **Dependencies:** M2-T01
- **Acceptance Criteria:** `from app.ingestion.ast_parser import CodeUnit, ChunkType` works. A `CodeUnit` can be created and its fields accessed correctly.
- **Estimated Time:** 15 min

---

### M2-T03 — Python AST parser `[BE]`
- **Description:** In `ast_parser.py`, implement `parse_python(file_path: str, content: str) -> list[CodeUnit]`. Use tree-sitter Python grammar to extract: (1) module header (first docstring + imports block, lines 1 to first non-import); (2) top-level functions; (3) classes (declaration + class docstring only, not methods); (4) methods within classes (with `parent_name` set to class name). Each unit captures exact `line_start` and `line_end` from the AST node's position.
- **Files to modify:** `backend/app/ingestion/ast_parser.py`
- **Dependencies:** M2-T02
- **Acceptance Criteria:** Parsing a 100-line Python file with 2 classes and 5 standalone functions returns at least 8 `CodeUnit` objects. Each unit has correct `line_start`/`line_end`. Methods have `parent_name` set. No overlapping line ranges.
- **Estimated Time:** 40 min

---

### M2-T04 — JavaScript/TypeScript AST parser `[BE]`
- **Description:** In `ast_parser.py`, implement `parse_javascript(file_path, content, language) -> list[CodeUnit]` handling both `.js`/`.jsx` and `.ts`/`.tsx`. Extract: function declarations, arrow functions assigned to `const`, class declarations, class methods. For `.tsx`/`.jsx`, also extract React component functions (exported functions returning JSX). Handle TypeScript-specific syntax (interfaces and type aliases as `BLOCK` chunks).
- **Files to modify:** `backend/app/ingestion/ast_parser.py`
- **Dependencies:** M2-T02
- **Acceptance Criteria:** Parsing a 50-line Express router file returns route handler functions as `CodeUnit` objects. Parsing a React component file returns the component as a `FUNCTION` chunk.
- **Estimated Time:** 35 min

---

### M2-T05 — Go + Java AST parsers `[BE]`
- **Description:** In `ast_parser.py`, implement `parse_go(file_path, content) -> list[CodeUnit]` and `parse_java(file_path, content) -> list[CodeUnit]`. Go: extract functions, methods (on types), and struct declarations. Java: extract class declarations and methods within classes (with `parent_name`). Both use their respective tree-sitter grammars.
- **Files to modify:** `backend/app/ingestion/ast_parser.py`
- **Dependencies:** M2-T02
- **Acceptance Criteria:** Parsing a Go file with 3 functions and 1 struct returns at least 4 `CodeUnit` objects. Parsing a Java class with 4 methods returns 4 method units with correct `parent_name`.
- **Estimated Time:** 35 min

---

### M2-T06 — Fallback text chunker + main `parse_file` dispatcher `[BE]`
- **Description:** In `ast_parser.py`, implement `parse_fallback(file_path, content, language) -> list[CodeUnit]` that does line-based splitting into ~400-line blocks (with no AST awareness) as `BLOCK` type chunks. Implement the public `parse_file(file_path: str, content: str) -> list[CodeUnit]` dispatcher that routes to the correct parser by extension or calls fallback. Also handle Rust (reuse Go parser structure with `tree-sitter-rust`).
- **Files to modify:** `backend/app/ingestion/ast_parser.py`
- **Dependencies:** M2-T03, M2-T04, M2-T05
- **Acceptance Criteria:** `parse_file("README.md", content)` returns at least one `BLOCK` chunk. `parse_file("main.py", content)` routes to the Python parser. `parse_file("unknown.xyz", content)` calls fallback without error.
- **Estimated Time:** 25 min

---

### M2-T07 — Token counter utility `[BE]`
- **Description:** Add `tiktoken` to `requirements.txt`. Create `ingestion/token_counter.py` with a single function `count_tokens(text: str) -> int` that uses `tiktoken.get_encoding("cl100k_base")`. Cache the encoder at module level (do not reload per call). This utility is used by the chunker.
- **Files to create:** `backend/app/ingestion/token_counter.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** `count_tokens("hello world")` returns a small integer. The function is fast (< 10ms for a 500-token string). The encoder is loaded once at import, not per call.
- **Estimated Time:** 15 min

---

### M2-T08 — Chunker `[BE]`
- **Description:** Implement `ingestion/chunker.py`. Define a `Chunk` dataclass (inherits metadata from `CodeUnit` plus `content: str`, `sub_index: int | None`, `sub_total: int | None`). Implement `chunk_code_unit(unit: CodeUnit) -> list[Chunk]`: if `count_tokens(unit.content) <= 512`, return one chunk; otherwise, split with `RecursiveCharacterTextSplitter` from `langchain-text-splitters` (chunk_size=512, overlap=64, length_function=count_tokens) and prefix each sub-chunk with `# File: {path}, {type} '{name}', Lines: {start}-{end} (part {i+1} of {n})`.
- **Files to create:** `backend/app/ingestion/chunker.py`
- **Dependencies:** M2-T02, M2-T07
- **Acceptance Criteria:** A 100-token function produces 1 chunk with no prefix. A 1200-token function produces 3 chunks, each under 512 tokens, each prefixed with location context. `chunk_code_unit` is deterministic given the same input.
- **Estimated Time:** 35 min

---

### M2-T09 — sentence-transformers embedder `[BE]`
- **Description:** Add `sentence-transformers`, `faiss-cpu`, `numpy` to `requirements.txt`. Implement `ingestion/embedder.py`. Define an `Embedder` class. `__init__` loads `BAAI/bge-small-en-v1.5` via `SentenceTransformer` (model is cached to `~/.cache/huggingface` on first run). Define `embed_batch(texts: list[str]) -> np.ndarray` that calls `model.encode(texts, batch_size=64, normalize_embeddings=True, show_progress_bar=False)` and returns a float32 numpy array of shape `(n, 384)`.
- **Files to create:** `backend/app/ingestion/embedder.py`
- **Dependencies:** M1-T01
- **Acceptance Criteria:** `Embedder().embed_batch(["hello world"])` returns a numpy array of shape `(1, 384)`. Encoding 128 sentences takes < 30 seconds on CPU. The model is not reloaded between calls.
- **Estimated Time:** 25 min

---

### M2-T10 — FAISS index builder and persistence `[BE]`
- **Description:** In `ingestion/embedder.py`, add class `FAISSStore`. `create_index(embeddings: np.ndarray, chunk_ids: list[int]) -> None` builds a `faiss.IndexFlatIP` (inner product, for cosine similarity with normalized vectors), adds all embeddings, and saves to `data/faiss/{project_id}.faiss`. Also saves `data/faiss/{project_id}.meta.json` mapping `faiss_index_position -> chunk_db_id`. `save()` and `load(project_id)` methods handle persistence.
- **Files to modify:** `backend/app/ingestion/embedder.py`
- **Dependencies:** M2-T09
- **Acceptance Criteria:** After calling `create_index`, the `.faiss` and `.meta.json` files exist on disk. `FAISSStore.load(project_id)` reloads the index correctly. The index size matches the number of chunks added.
- **Estimated Time:** 30 min

---

### M2-T11 — FAISS search service `[BE]`
- **Description:** Implement `search/service.py`. Define `search(query: str, project_id: int, db: AsyncSession, top_k: int = 8) -> list[dict]`. It: (1) instantiates `Embedder` and embeds the query as a single vector; (2) loads `FAISSStore` for the project; (3) calls `index.search(query_vec, top_k)` to get distances and FAISS positions; (4) maps positions to chunk IDs via the `.meta.json`; (5) fetches `ProjectChunk` records from SQLite and returns them with `score` attached.
- **Files to create:** `backend/app/search/service.py`
- **Dependencies:** M2-T10, M1-T04
- **Acceptance Criteria:** Given a project with an ingested codebase, `search("authentication", project_id, db)` returns 8 dicts, each with `file_path`, `content`, `line_start`, `line_end`, `score`. Results for "authentication" include chunks from auth-related files.
- **Estimated Time:** 30 min

---

### M2-T12 — Metadata persistence (project_files + project_chunks) `[BE]`
- **Description:** In `ingestion/pipeline.py`, after chunking and embedding, add the metadata persistence step: (1) for each file, upsert a `ProjectFile` record; (2) for each chunk, insert a `ProjectChunk` record with `faiss_index` = the position in the FAISS array. Update `project.total_chunks` and `project.faiss_index_path` after index creation. This step runs after `FAISSStore.create_index`.
- **Files to modify:** `backend/app/ingestion/pipeline.py`
- **Dependencies:** M2-T10, M1-T07, M1-T04
- **Acceptance Criteria:** After ingesting a project, `SELECT COUNT(*) FROM project_chunks WHERE project_id=1` returns a positive number. Every chunk has a valid `faiss_index` value. `faiss_index_path` on the project record points to an existing file.
- **Estimated Time:** 25 min

---

### M2-T13 — Wire full ingestion pipeline (stages 3–5) `[BE]`
- **Description:** Update `ingestion/pipeline.py` to wire in all stages after file walking: for each discovered file, call `parse_file` → `chunk_code_unit` per unit → collect all chunks → batch embed all chunks → `FAISSStore.create_index` → persist metadata. Update `ingestion_progress` in the project record at each stage: 20% after walk, 50% after parsing, 80% after embedding, 100% on completion. Handle `Exception` at each stage and transition to `failed` status with the error message.
- **Files to modify:** `backend/app/ingestion/pipeline.py`
- **Dependencies:** M2-T06, M2-T08, M2-T11, M2-T12
- **Acceptance Criteria:** `POST /projects/1/ingest` on a 50-file Python project sets status to `ready` and populates both FAISS and SQLite. `GET /projects/1/status` shows `ingestion_progress: 100`. A bad URL sets `status: "failed"` with a message.
- **Estimated Time:** 30 min

---

### M2-T14 — Search router `[BE]`
- **Description:** Implement `search/router.py` with a single endpoint: `GET /projects/{project_id}/search?q=...&top_k=8`. It calls `search_service.search(q, project_id, db)` and returns the list of chunk results. Register in `main.py`. Return 404 if the project does not exist or is not in `ready` status. Return 400 if `q` is empty.
- **Files to create/modify:** `backend/app/search/router.py`, `backend/app/main.py`
- **Dependencies:** M2-T11, M1-T07
- **Acceptance Criteria:** `GET /projects/1/search?q=authentication` returns a JSON array of chunks. Each chunk has `file_path`, `line_start`, `line_end`, `content`, `score`. Returns 400 for empty `q`.
- **Estimated Time:** 20 min

---

### M2-T15 — Unit tests: parser + chunker `[BE]`
- **Description:** Create `backend/tests/test_ast_parser.py` and `backend/tests/test_chunker.py`. Parser tests: use small fixture strings (inline, not files) for Python, JS, and fallback. Assert expected number of `CodeUnit` objects, correct `chunk_type`, and non-empty `content`. Chunker tests: assert that a short unit produces 1 chunk, a long unit produces multiple, and sub-chunk prefixes contain the correct location info. Install `pytest` and `pytest-asyncio` in requirements.
- **Files to create:** `backend/tests/test_ast_parser.py`, `backend/tests/test_chunker.py`, `backend/tests/conftest.py`
- **Dependencies:** M2-T06, M2-T08
- **Acceptance Criteria:** `pytest tests/test_ast_parser.py tests/test_chunker.py` passes with 0 failures. At least 6 test cases in each file.
- **Estimated Time:** 30 min

---

### M2-T16 — Unit test: FAISS search `[BE]`
- **Description:** Create `backend/tests/test_search.py`. Build a small in-memory FAISS index with 10 known chunks (using the `Embedder` + `FAISSStore`). Assert that querying for a term that appears in one chunk returns that chunk in the top 3 results. Assert that returned results have all required fields. Use `tmp_path` pytest fixture for the index file to avoid leaving test artifacts.
- **Files to create:** `backend/tests/test_search.py`
- **Dependencies:** M2-T11, M2-T15
- **Acceptance Criteria:** `pytest tests/test_search.py` passes. The test does not require an internet connection (uses locally cached model or mocks the embedder).
- **Estimated Time:** 25 min

---

## Milestone 3 — AI Chat
**Goal:** Full RAG-powered, streaming, multi-turn chat with source citations.

---

### M3-T01 — Gemini SDK setup + smoke test `[BE]`
- **Description:** Add `google-generativeai` to `requirements.txt`. In `chat/llm_client.py`, write a standalone function `_test_gemini()` (not part of the API) that creates a `genai.GenerativeModel("gemini-1.5-flash")`, calls `generate_content("Say hello")`, and prints the response. Verify it works with a real `GEMINI_API_KEY` loaded from `.env`. Then delete the test function — it was only for environment validation.
- **Files to create:** `backend/app/chat/llm_client.py` (partial)
- **Dependencies:** M1-T13
- **Acceptance Criteria:** Running the smoke test script with a valid key prints a response. The key is read from env, not hardcoded. This task is complete when you can confirm the SDK works in your environment.
- **Estimated Time:** 15 min

---

### M3-T02 — Groq SDK setup + smoke test `[BE]`
- **Description:** Add `groq` to `requirements.txt`. In `chat/llm_client.py`, write a standalone smoke test function for `groq.Groq().chat.completions.create(model="llama-3.1-8b-instant", messages=[...])`. Verify it works with a real `GROQ_API_KEY`. Delete the test function after verification.
- **Files to modify:** `backend/app/chat/llm_client.py` (partial)
- **Dependencies:** M1-T13
- **Acceptance Criteria:** Groq API call succeeds with a valid key. Can be run independently of Gemini setup.
- **Estimated Time:** 15 min

---

### M3-T03 — LLM client — Gemini streaming `[BE]`
- **Description:** In `chat/llm_client.py`, implement `async def stream_gemini(messages: list[dict], system_prompt: str) -> AsyncGenerator[str, None]`. Use `google.generativeai` with `stream=True`. Convert the `messages` list (role/content dicts) to the Gemini `ChatSession` format. Yield each text chunk as it arrives. Raise a custom `LLMRateLimitError` on HTTP 429 and a `LLMError` on other failures.
- **Files to modify:** `backend/app/chat/llm_client.py`
- **Dependencies:** M3-T01
- **Acceptance Criteria:** `stream_gemini([{"role": "user", "content": "Say hi"}], "You are helpful")` is an async generator that yields string tokens. Tokens arrive incrementally (not all at once).
- **Estimated Time:** 30 min

---

### M3-T04 — LLM client — Groq fallback + retry logic `[BE]`
- **Description:** In `chat/llm_client.py`, implement `async def stream_groq(messages: list[dict], system_prompt: str) -> AsyncGenerator[str, None]` using `groq.AsyncGroq`. Also implement the top-level `async def stream_llm(messages, system_prompt) -> AsyncGenerator[str, None]` that: (1) tries `stream_gemini`; (2) on `LLMRateLimitError`, waits 4 seconds and retries once; (3) on second failure, calls `stream_groq`; (4) on `LLMRateLimitError` from Groq, uses exponential backoff (2s, 4s) with max 2 retries; (5) if all fail, yields a single error message string.
- **Files to modify:** `backend/app/chat/llm_client.py`
- **Dependencies:** M3-T02, M3-T03
- **Acceptance Criteria:** `stream_llm` is the only function called by higher layers. Simulating a 429 from Gemini causes a logged fallback to Groq (verifiable in console). The caller never sees a raw exception — only the error message string.
- **Estimated Time:** 30 min

---

### M3-T05 — Prompt builder — context injection `[BE]`
- **Description:** Implement `chat/prompt_builder.py`. Define `SYSTEM_PROMPT` as a module-level string: instructs the model to only answer from provided context, always cite `[file: path, lines: X-Y]` for every claim, and explicitly acknowledge when context is insufficient. Define `build_context_block(chunks: list[dict]) -> str` that formats retrieved chunks as a structured context block with file path, line range, and code content per chunk.
- **Files to create:** `backend/app/chat/prompt_builder.py`
- **Dependencies:** M2-T11
- **Acceptance Criteria:** `build_context_block([{"file_path": "auth.py", "line_start": 1, "line_end": 10, "content": "..."}])` returns a non-empty string with the file path visible. The system prompt contains explicit citation instructions.
- **Estimated Time:** 20 min

---

### M3-T06 — Prompt builder — conversation history `[BE]`
- **Description:** In `prompt_builder.py`, implement `build_messages(question: str, context_block: str, history: list[dict]) -> list[dict]`. Take the last 6 messages from `history` (3 turns). Build a `messages` list in `[{"role": "user"|"assistant", "content": "..."}]` format. Inject the `context_block` into the content of the first user message in the current turn: `f"CONTEXT:\n{context_block}\n\nQUESTION:\n{question}"`. Return the complete messages list.
- **Files to modify:** `backend/app/chat/prompt_builder.py`
- **Dependencies:** M3-T05
- **Acceptance Criteria:** `build_messages("What is this?", context, [])` returns a list with one user message containing both the context and question. With 6 history messages provided, the returned list has 7 messages (6 history + 1 current).
- **Estimated Time:** 20 min

---

### M3-T07 — Chat service — RAG orchestration `[BE]`
- **Description:** Implement `chat/service.py`. Define `async def get_or_create_conversation(project_id, conversation_id, question, db) -> Conversation`. Define the main `async def process_chat(project_id, conversation_id, question, db) -> AsyncGenerator[str, None]`: (1) call `search_service.search(question, project_id, db, top_k=8)` to retrieve context; (2) fetch last 6 messages from DB for history; (3) call `prompt_builder.build_messages`; (4) call `llm_client.stream_llm`; (5) collect the full response while yielding tokens; (6) parse `[file: ..., lines: ...]` citation patterns from the completed response using regex; (7) persist both user message and assistant message with citations to SQLite.
- **Files to create:** `backend/app/chat/service.py`
- **Dependencies:** M2-T11, M3-T04, M3-T06, M1-T04
- **Acceptance Criteria:** `process_chat` is an async generator. Calling it on a project with an auth module and asking "how does auth work" yields tokens and eventually persists a message with citations in the DB.
- **Estimated Time:** 40 min

---

### M3-T08 — Chat SSE endpoint `[BE]`
- **Description:** Implement `chat/router.py`. Define `POST /projects/{project_id}/chat` that accepts `{ "message": str, "conversation_id": int | null }`. Use FastAPI `StreamingResponse` with `media_type="text/event-stream"`. The generator wraps `chat_service.process_chat` and formats each token as `data: {"type": "token", "token": "..."}\n\n`. On completion, send `data: {"type": "done", "conversation_id": N}\n\n`. Register in `main.py`.
- **Files to create/modify:** `backend/app/chat/router.py`, `backend/app/main.py`
- **Dependencies:** M3-T07
- **Acceptance Criteria:** `curl -N -X POST localhost:8000/projects/1/chat -H "Content-Type: application/json" -d '{"message":"what is this project?"}' ` streams SSE events to the terminal. Each event is a valid JSON object. The last event has `"type": "done"`.
- **Estimated Time:** 25 min

---

### M3-T09 — Conversation history endpoints `[BE]`
- **Description:** In `chat/router.py`, add: `GET /projects/{project_id}/conversations` returns list of conversations for that project (sorted by `created_at DESC`); `GET /projects/{project_id}/conversations/{conv_id}` returns the conversation with all messages (each message includes `citations` parsed from JSON). Add corresponding Pydantic schemas in `schemas.py`: `ConversationResponse`, `MessageResponse`.
- **Files to modify:** `backend/app/chat/router.py`, `backend/app/schemas.py`
- **Dependencies:** M3-T08
- **Acceptance Criteria:** After chatting, `GET /projects/1/conversations` returns a non-empty list. `GET /projects/1/conversations/1` returns all messages with correct roles and content.
- **Estimated Time:** 25 min

---

### M3-T10 — Frontend SSE streaming client `[FE]`
- **Description:** Implement `frontend/src/lib/streaming.ts`. Export `streamChat(projectId, message, conversationId?, onToken, onDone, onError)`. Use the browser `EventSource` API (or `fetch` with `ReadableStream` for POST requests, since `EventSource` is GET-only). Parse SSE events: call `onToken(token)` for each `type: "token"` event, and `onDone(conversationId)` for `type: "done"`. Handle network errors and call `onError`.
- **Files to create:** `frontend/src/lib/streaming.ts`
- **Dependencies:** M1-T15
- **Acceptance Criteria:** `streamChat` correctly parses streamed SSE events in a browser context. Tokens arrive and `onToken` is called once per token. `onDone` is called exactly once at the end.
- **Estimated Time:** 30 min

---

### M3-T11 — MessageBubble component `[FE]`
- **Description:** Create `frontend/src/components/MessageBubble.tsx`. Render a single chat message with: role-based styling (user = right-aligned blue, assistant = left-aligned grey); markdown rendering for assistant messages (use `react-markdown`); citation parsing — detect `[file: path, lines: X-Y]` patterns in content and render them as clickable `<button>` elements (styled as inline badges). Clicking a citation calls `onCitationClick(filePath, lineStart)` prop.
- **Files to create:** `frontend/src/components/MessageBubble.tsx`
- **Dependencies:** M1-T14
- **Acceptance Criteria:** User messages render right-aligned. Assistant messages render markdown (bold, code blocks). Citation `[file: auth.py, lines: 10-20]` appears as a clickable badge, not raw text.
- **Estimated Time:** 35 min

---

### M3-T12 — ChatInterface component `[FE]`
- **Description:** Create `frontend/src/components/ChatInterface.tsx`. Manage local state for: `messages: Message[]`, `isStreaming: boolean`, `currentStreamText: string`. Render a scrollable message list of `MessageBubble` components. At the bottom: a textarea input and "Send" button. On send: append user message immediately, call `streamChat`, append a streaming assistant message that updates in real-time via `onToken`. Auto-scroll to bottom on new messages. Disable input while `isStreaming`.
- **Files to create:** `frontend/src/components/ChatInterface.tsx`
- **Dependencies:** M3-T10, M3-T11
- **Acceptance Criteria:** Sending a message shows the user's message immediately. Assistant response streams in token-by-token. Input is disabled during streaming. The message list auto-scrolls.
- **Estimated Time:** 40 min

---

### M3-T13 — ConversationList + Chat page `[FE]`
- **Description:** Create `frontend/src/components/ConversationList.tsx` that fetches and lists past conversations for a project with a "New Chat" button. Implement `frontend/src/app/projects/[id]/chat/page.tsx` that renders `ConversationList` in a left sidebar and `ChatInterface` as the main content. Selecting a conversation from the list loads its history into `ChatInterface`. "New Chat" clears the `ChatInterface` and starts with no `conversationId`.
- **Files to create:** `frontend/src/components/ConversationList.tsx`, `frontend/src/app/projects/[id]/chat/page.tsx`
- **Dependencies:** M3-T09, M3-T12
- **Acceptance Criteria:** Chat page loads with the conversation list on the left. Clicking a past conversation loads its messages. "New Chat" starts a fresh session. The correct `conversationId` is passed to `streamChat` for continuations.
- **Estimated Time:** 30 min

---

## Milestone 4 — File Explorer + Code Viewer
**Goal:** The codebase is fully navigable. Citations in chat are clickable and jump to the correct file and line.

---

### M4-T01 — File tree endpoint `[BE]`
- **Description:** In `projects/router.py`, add `GET /projects/{project_id}/files`. Query all `ProjectFile` records for the project. Build a nested tree structure: split each `file_path` by `/` and build a recursive `{ path, type: "file"|"directory", language, children: [] }` structure. Return the root nodes. Files in the same directory are grouped under a directory node.
- **Files to modify:** `backend/app/projects/router.py`
- **Dependencies:** M2-T12, M1-T07
- **Acceptance Criteria:** `GET /projects/1/files` returns a nested JSON tree. A project with files in `src/auth/`, `src/api/`, and root returns directory nodes for `src/`, `src/auth/`, `src/api/`. Each file node has `language` set.
- **Estimated Time:** 30 min

---

### M4-T02 — File content endpoint `[BE]`
- **Description:** In `projects/router.py`, add `GET /projects/{project_id}/files/content?path=src/auth.py`. Look up the project's `repo_path` from the DB, resolve `repo_path / file_path`, read the file, and return `{ "content": "...", "language": "python", "line_count": 187 }`. Validate that the resolved path is within `repo_path` (path traversal protection). Return 404 if the file does not exist.
- **Files to modify:** `backend/app/projects/router.py`
- **Dependencies:** M4-T01
- **Acceptance Criteria:** `GET /projects/1/files/content?path=src/main.py` returns the raw file content. Requesting `?path=../../etc/passwd` returns 400. Missing files return 404.
- **Estimated Time:** 20 min

---

### M4-T03 — Language breakdown endpoint `[BE]`
- **Description:** In `projects/router.py`, add `GET /projects/{project_id}/languages`. Aggregate `ProjectFile.language` counts for the project, compute percentages, and return `[{ "language": "Python", "percent": 65.2, "file_count": 34 }]` sorted by percentage descending. This powers the language stat bar in the UI.
- **Files to modify:** `backend/app/projects/router.py`
- **Dependencies:** M4-T01
- **Acceptance Criteria:** Returns a non-empty list for any ingested project. Percentages sum to 100. Languages are sorted by percentage.
- **Estimated Time:** 15 min

---

### M4-T04 — FileExplorer component `[FE]`
- **Description:** Create `frontend/src/components/FileExplorer.tsx`. Fetch `GET /projects/:id/files` and render a collapsible tree. Directories are collapsible (click to expand/collapse, default expanded for top-level). Files show a language icon (use `lucide-react` icons: `FileCode`, `FileText`, etc.). Clicking a file calls `onFileSelect(filePath)` prop. Show a loading skeleton while fetching.
- **Files to create:** `frontend/src/components/FileExplorer.tsx`
- **Dependencies:** M4-T01, M1-T14
- **Acceptance Criteria:** Directory nodes collapse/expand on click. Clicking a file triggers `onFileSelect`. The tree correctly nests files for a project with 3 levels of directories. Loading skeleton visible during fetch.
- **Estimated Time:** 40 min

---

### M4-T05 — CodeViewer component `[FE]`
- **Description:** Create `frontend/src/components/CodeViewer.tsx`. Install `@monaco-editor/react`. Render Monaco Editor in read-only mode. Accept `filePath: string`, `language: string`, and `highlightLine: number | null` as props. When `highlightLine` changes, programmatically scroll the editor to that line and add a background highlight on that line (using Monaco's `deltaDecorations` API). Show a placeholder "Select a file to view" when no file is selected.
- **Files to create:** `frontend/src/components/CodeViewer.tsx`
- **Dependencies:** M1-T14
- **Acceptance Criteria:** Opening a Python file renders syntax-highlighted code. Programmatically setting `highlightLine={42}` scrolls to line 42 and highlights it in yellow. Monaco is read-only (no editing possible).
- **Estimated Time:** 40 min

---

### M4-T06 — Project layout with explorer + viewer `[FE]`
- **Description:** Implement `frontend/src/app/projects/[id]/layout.tsx`. Create a three-panel layout: left panel (fixed width) = `FileExplorer`; center panel = page content (`{children}`); right panel (conditional) = `CodeViewer` that appears when a file is selected or a citation is clicked. Manage `selectedFile` and `highlightLine` state at the layout level. Pass `onCitationClick` down via React context so `MessageBubble` (in the chat page) can trigger the code viewer from anywhere.
- **Files to create:** `frontend/src/app/projects/[id]/layout.tsx`
- **Dependencies:** M4-T04, M4-T05
- **Acceptance Criteria:** Three-panel layout renders on all project sub-pages. Clicking a file in the explorer opens it in the right panel. The code viewer panel opens and closes correctly.
- **Estimated Time:** 35 min

---

### M4-T07 — Wire citation clicks to CodeViewer `[FE]`
- **Description:** Create `frontend/src/lib/CitationContext.tsx` — a React context with `openFile(filePath: string, line: number) => void`. Provide this context in the project layout (wired to `selectedFile` / `highlightLine` state). Consume it in `MessageBubble.tsx` — replace the `onCitationClick` prop with a `useContext(CitationContext)` call so citations work from any depth in the tree.
- **Files to create:** `frontend/src/lib/CitationContext.tsx`
- **Files to modify:** `frontend/src/app/projects/[id]/layout.tsx`, `frontend/src/components/MessageBubble.tsx`
- **Dependencies:** M4-T06, M3-T11
- **Acceptance Criteria:** Clicking a citation `[file: src/auth.py, lines: 42-67]` in the chat opens `src/auth.py` in the right-side CodeViewer scrolled to line 42 with the line highlighted.
- **Estimated Time:** 20 min

---

### M4-T08 — Language stat bar + project overview page `[FE]`
- **Description:** Implement `frontend/src/app/projects/[id]/page.tsx`. Show: project name, status, total files, total chunks, creation date. Fetch `GET /projects/:id/languages` and render a horizontal stacked bar chart showing language distribution with color coding and labels (each language gets a distinct color from a fixed palette).
- **Files to create:** `frontend/src/app/projects/[id]/page.tsx`
- **Dependencies:** M4-T03, M4-T06
- **Acceptance Criteria:** The project overview page shows all metadata. The language bar displays proportional segments. Hovering a segment shows the language name and percentage (tooltip).
- **Estimated Time:** 25 min

---

## Milestone 5 — Generation Features
**Goal:** Architecture summary, API endpoint discovery, doc generation, and dependency graph all work end-to-end.

---

### M5-T01 — Framework detector `[BE]`
- **Description:** Implement `generation/framework_detector.py`. Define `detect_framework(project_id, db) -> dict`. Query `ProjectFile` for config file names: `package.json`, `requirements.txt`, `go.mod`, `pom.xml`, `Gemfile`, `Cargo.toml`, `pyproject.toml`. Check for framework-specific files (`manage.py`=Django, presence of `fastapi` in requirements=FastAPI, `express` in package.json=Express). Return `{ "language": "Python", "framework": "FastAPI", "test_framework": "pytest", "has_docker": true }`.
- **Files to create:** `backend/app/generation/framework_detector.py`
- **Dependencies:** M2-T12
- **Acceptance Criteria:** Returns `framework: "FastAPI"` for the `tiangolo/fastapi` repo. Returns `framework: "Express"` for `expressjs/express`. Returns `framework: "unknown"` gracefully for unrecognized repos.
- **Estimated Time:** 25 min

---

### M5-T02 — Architecture analyzer `[BE]`
- **Description:** Implement `generation/architecture.py`. Define `async def generate_architecture_summary(project_id, db) -> dict`. Steps: (1) use `detect_framework` to get stack info; (2) fetch content of key files (README, main entry point, config files) via file content lookup; (3) sample 2 files from each top-level directory (use FAISS search with queries like "main entry point", "database connection", "route registration"); (4) build a prompt with all gathered context; (5) call `llm_client.stream_llm` and collect the full (non-streaming) response; (6) return `{ summary, stack, layers }`.
- **Files to create:** `backend/app/generation/architecture.py`
- **Dependencies:** M5-T01, M3-T04, M2-T11
- **Acceptance Criteria:** Returns a non-empty `summary` string. `stack` includes detected language and framework. `layers` has at least 2 entries for any real project.
- **Estimated Time:** 35 min

---

### M5-T03 — API endpoint scanner `[BE]`
- **Description:** Implement `generation/api_scanner.py`. Define `scan_api_endpoints(project_id, db) -> list[dict]`. Phase 1: regex patterns over all `ProjectChunk.content` for the project — patterns for FastAPI (`@router.get/post`), Express (`router.get/post/put/delete`), Django (`path(...)`), Spring (`@GetMapping`). Collect all matching chunks. Phase 2: for matched chunks, call `llm_client` (non-streaming) to extract `{ method, path, handler, description }` per match. Deduplicate by `(method, path)`. Return sorted list.
- **Files to create:** `backend/app/generation/api_scanner.py`
- **Dependencies:** M3-T04, M1-T04
- **Acceptance Criteria:** Scanning `tiangolo/fastapi`'s example code finds route definitions. Scanning `expressjs/express` examples finds Express routes. No duplicates in the returned list.
- **Estimated Time:** 40 min

---

### M5-T04 — Documentation generator `[BE]`
- **Description:** Implement `generation/doc_generator.py`. Define `async def generate_docstring(project_id, file_path, function_name, db) -> AsyncGenerator[str, None]`. Look up the `ProjectChunk` by `(project_id, file_path, name=function_name)`. Get the `language` from `ProjectFile`. Build a prompt: "Generate a {language} docstring for the following function. Use {Google-style for Python / JSDoc for JS/TS}. Return only the docstring, no explanation." Stream the response via `llm_client.stream_llm`.
- **Files to create:** `backend/app/generation/doc_generator.py`
- **Dependencies:** M3-T04, M1-T04
- **Acceptance Criteria:** Returns a streaming response for a known function. The response is a valid Python docstring for a Python function. The response is valid JSDoc for a JS function.
- **Estimated Time:** 25 min

---

### M5-T05 — Generation router `[BE]`
- **Description:** Implement `generation/router.py` with four endpoints: `GET /projects/{id}/architecture` (calls `generate_architecture_summary`, returns JSON); `GET /projects/{id}/api-endpoints` (calls `scan_api_endpoints`, returns JSON list); `POST /projects/{id}/generate/docs` with body `{ file_path, function_name }` (calls `generate_docstring`, returns SSE stream); all return 404 for unknown projects and 400 if project is not `ready`. Register in `main.py`.
- **Files to create/modify:** `backend/app/generation/router.py`, `backend/app/main.py`
- **Dependencies:** M5-T02, M5-T03, M5-T04
- **Acceptance Criteria:** All four endpoints appear in Swagger UI. `GET /projects/1/architecture` returns a JSON response. `GET /projects/1/api-endpoints` returns a JSON array. The docs endpoint streams SSE.
- **Estimated Time:** 25 min

---

### M5-T06 — Dependency graph builder `[BE]`
- **Description:** Implement `graph/builder.py`. Define `build_dependency_graph(project_id, db) -> dict`. For each `ProjectChunk` with `chunk_type = "MODULE"`, run language-specific import extraction regex: Python (`import X`, `from X import Y`), JS/TS (`import ... from 'X'`, `require('X')`), Go (`import "X"`). Map import paths to actual project files (resolve relative imports using the source file's directory). Build `{ nodes: [{id, label, language}], edges: [{source, target}] }`.
- **Files to create:** `backend/app/graph/builder.py`
- **Dependencies:** M2-T12
- **Acceptance Criteria:** Builds a graph for any Python project. Node IDs are file paths. Edges represent actual imports resolved to files in the project (external library imports are excluded or marked as external nodes). Graph has no duplicate edges.
- **Estimated Time:** 40 min

---

### M5-T07 — Cycle detector `[BE]`
- **Description:** Implement `graph/cycle_detector.py`. Define `detect_cycles(edges: list[dict]) -> list[list[str]]` using DFS-based cycle detection (track visited + recursion stack). Return a list of cycles, where each cycle is a list of file paths. Mark nodes involved in cycles in the graph data. Add a `is_circular` boolean field to each node in the graph output.
- **Files to create:** `backend/app/graph/cycle_detector.py`
- **Dependencies:** M5-T06
- **Acceptance Criteria:** A graph with `A→B→C→A` returns `[["A", "B", "C"]]`. A graph with no cycles returns `[]`. Nodes in cycles have `is_circular: true` in the output.
- **Estimated Time:** 25 min

---

### M5-T08 — Graph router `[BE]`
- **Description:** Implement `graph/router.py` with `GET /projects/{id}/graph`. Calls `build_dependency_graph` then `detect_cycles`. Returns the full graph with `{ nodes, edges, circularDependencies }`. Register in `main.py`. Return 400 if project is not `ready`.
- **Files to create/modify:** `backend/app/graph/router.py`, `backend/app/main.py`
- **Dependencies:** M5-T07
- **Acceptance Criteria:** `GET /projects/1/graph` returns a JSON object with `nodes` and `edges` arrays. For a project with files that import each other, edges appear. Response time is under 5 seconds for a 200-file project.
- **Estimated Time:** 15 min

---

### M5-T09 — Generation page — architecture + API endpoints tabs `[FE]`
- **Description:** Implement `frontend/src/app/projects/[id]/generate/page.tsx`. Use shadcn `Tabs` with three tabs: "Architecture", "API Endpoints", "Documentation". Architecture tab: fetch `GET /projects/:id/architecture` on tab activate; render `summary` as prose, `stack` as a key-value table, `layers` as a list. API Endpoints tab: fetch `GET /projects/:id/api-endpoints`; render a table with Method (colored badge), Path, Handler, Description columns sorted by path.
- **Files to create:** `frontend/src/app/projects/[id]/generate/page.tsx`
- **Dependencies:** M5-T05, M4-T06
- **Acceptance Criteria:** Architecture tab shows prose summary and stack table after loading. API Endpoints tab shows a table with HTTP method badges (GET=green, POST=blue, DELETE=red). Both tabs show loading spinners while fetching.
- **Estimated Time:** 30 min

---

### M5-T10 — Generation page — documentation tab `[FE]`
- **Description:** In the generate page, implement the "Documentation" tab. Fetch `GET /projects/:id/files` to populate a file selector dropdown. On file select, fetch `GET /projects/:id/files/content` and parse function names (look for function/class names in the content — simple regex is fine here). Show a second dropdown to select the function. On "Generate" click, call `POST /projects/:id/generate/docs` and stream the result into a code block with the appropriate language. Include a "Copy" button.
- **Files to modify:** `frontend/src/app/projects/[id]/generate/page.tsx`
- **Dependencies:** M5-T09, M3-T10
- **Acceptance Criteria:** User can select a file, select a function, and see a streamed docstring appear. Copy button copies the output to clipboard. The code block uses appropriate syntax highlighting.
- **Estimated Time:** 30 min

---

### M5-T11 — DependencyGraph component `[FE]`
- **Description:** Create `frontend/src/components/DependencyGraph.tsx`. Install `reactflow`. Fetch `GET /projects/:id/graph` and map nodes/edges to React Flow format. Use `dagre` layout algorithm (install `dagre`) for automatic positioning. Node colors: normal=blue, circular=red. Clicking a node calls `openFile(filePath, 1)` from `CitationContext`. Enable zoom and pan. Show a legend (normal node / circular dependency). Render a loading skeleton while fetching.
- **Files to create:** `frontend/src/components/DependencyGraph.tsx`
- **Dependencies:** M5-T08, M4-T07
- **Acceptance Criteria:** Graph renders with correct nodes and directed edges. Circular dependency nodes appear red. Clicking a node opens the file in CodeViewer. Graph is zoomable and pannable. Does not crash for graphs with 100+ nodes.
- **Estimated Time:** 40 min

---

### M5-T12 — Graph page `[FE]`
- **Description:** Implement `frontend/src/app/projects/[id]/graph/page.tsx`. Render `DependencyGraph` full-height in the main content area. Show a summary panel: total nodes, total edges, circular dependency count. If circular deps > 0, show a warning banner listing the involved files.
- **Files to create:** `frontend/src/app/projects/[id]/graph/page.tsx`
- **Dependencies:** M5-T11
- **Acceptance Criteria:** Graph page renders the `DependencyGraph` component full-height. Summary panel shows correct counts. Circular dependency warning appears only when cycles exist.
- **Estimated Time:** 20 min

---

## Milestone 6 — Docker Deployment + Polish
**Goal:** Zero-configuration startup. Demo-ready on any machine with Docker and valid API keys.

---

### M6-T01 — Harden backend Dockerfile `[INFRA]`
- **Description:** Update `backend/Dockerfile` for production: (1) add a non-root user `appuser` and switch to it; (2) pre-download the HuggingFace model during the Docker build step (so the first run doesn't download it — add `RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('BAAI/bge-small-en-v1.5')"`); (3) set `PYTHONDONTWRITEBYTECODE=1` and `PYTHONUNBUFFERED=1`; (4) ensure `data/` directory exists inside the container and is writable by `appuser`.
- **Files to modify:** `backend/Dockerfile`
- **Dependencies:** M1-T20
- **Acceptance Criteria:** `docker build` succeeds. The built image does not need to download the model at runtime — first chat works instantly. The container process runs as `appuser`, not root.
- **Estimated Time:** 20 min

---

### M6-T02 — Harden frontend Dockerfile `[INFRA]`
- **Description:** Update `frontend/Dockerfile`: (1) add `output: "standalone"` to `next.config.ts` (reduces image size from ~500MB to ~100MB); (2) copy only the standalone output in the final stage; (3) set `NODE_ENV=production`; (4) add a non-root user.
- **Files to modify:** `frontend/Dockerfile`, `frontend/next.config.ts`
- **Dependencies:** M1-T21
- **Acceptance Criteria:** Built image is under 200MB. `docker run` starts the Next.js app successfully. `next.config.ts` has `output: "standalone"`.
- **Estimated Time:** 20 min

---

### M6-T03 — Final `docker-compose.yml` with volumes and healthchecks `[INFRA]`
- **Description:** Update `docker-compose.yml`: (1) add named volume `codesage_data` mounted at `/app/data` in the `api` service (ensures SQLite and FAISS persist); (2) add `healthcheck` to the `api` service (`curl -f http://localhost:8000/health || exit 1`, interval 30s, retries 3); (3) add `depends_on: { api: { condition: service_healthy } }` to the `web` service so it waits for the API; (4) add `restart: unless-stopped` to both services.
- **Files to modify:** `docker-compose.yml`
- **Dependencies:** M6-T01, M6-T02
- **Acceptance Criteria:** `docker-compose up` brings up both services. Data in `codesage_data` volume survives `docker-compose down && docker-compose up`. The frontend does not start until the API is healthy.
- **Estimated Time:** 20 min

---

### M6-T04 — Ingestion error handling + user-facing messages `[BE]`
- **Description:** Audit `ingestion/pipeline.py` for bare exceptions. Ensure each stage (clone, walk, parse, embed, store) has a specific `try/except` that: (1) sets `project.status = "failed"`; (2) sets `project.error_message` to a human-readable string (not a Python traceback). Add specific messages: "Could not clone repository — check the URL is a public GitHub repo", "Embedding failed — model may still be loading, try again", etc.
- **Files to modify:** `backend/app/ingestion/pipeline.py`
- **Dependencies:** M2-T13
- **Acceptance Criteria:** Ingesting an invalid GitHub URL sets status to `failed` with message "Could not clone repository...". The error message is visible in `GET /projects/1/status`. No Python tracebacks are ever sent to the frontend.
- **Estimated Time:** 25 min

---

### M6-T05 — Frontend error states `[FE]`
- **Description:** Add error handling throughout the frontend: (1) `CreateProjectModal` — if ingestion fails, show the `error_message` from the status poll in a red alert; (2) Chat page — if streaming fails or returns the error message token, show an inline error in the chat; (3) Generation page — if any generation endpoint fails, show a shadcn `Alert` with the error and a "Retry" button; (4) All API calls should catch errors and show a toast notification (use shadcn `Toaster`).
- **Files to modify:** `frontend/src/components/CreateProjectModal.tsx`, `frontend/src/components/ChatInterface.tsx`, `frontend/src/app/projects/[id]/generate/page.tsx`, `frontend/src/app/layout.tsx`
- **Dependencies:** M6-T04, M3-T12, M5-T09
- **Acceptance Criteria:** Entering an invalid GitHub URL, triggering ingestion, and watching it fail shows a red alert with the error message (not a blank screen or console error). Chat errors show inline. All API errors produce a toast.
- **Estimated Time:** 30 min

---

### M6-T06 — Loading skeletons + empty states `[FE]`
- **Description:** Add loading states: (1) `FileExplorer` — show a skeleton list of 5 lines while loading; (2) `DependencyGraph` — show "Building graph..." spinner while fetching; (3) Chat page — show "No conversations yet. Ask a question to get started." when conversation list is empty; (4) Dashboard — show "No projects yet. Create your first project." with the `CreateProjectModal` trigger when project list is empty; (5) Generation tabs — show skeleton while fetching.
- **Files to modify:** `frontend/src/components/FileExplorer.tsx`, `frontend/src/components/DependencyGraph.tsx`, multiple page files
- **Dependencies:** M4-T04, M5-T11, M3-T13, M1-T19
- **Acceptance Criteria:** All empty states render correctly. Loading skeletons are visible for at least 200ms during fetch (not a flash). No blank white boxes remain in the app.
- **Estimated Time:** 30 min

---

### M6-T07 — Ingestion progress stage labels `[BE]` + `[FE]`
- **Description:** Add a `current_stage_label` TEXT column to `projects` table via an Alembic migration. Update `pipeline.py` to set human-readable labels at each stage: "Cloning repository...", "Scanning files...", "Parsing source code...", "Generating embeddings...", "Saving to search index...", "Complete". Update `IngestionProgress.tsx` to display `current_stage_label` below the progress bar.
- **Files to modify:** `backend/app/ingestion/pipeline.py`, new Alembic migration, `frontend/src/components/IngestionProgress.tsx`
- **Dependencies:** M6-T03, M1-T18
- **Acceptance Criteria:** During ingestion, the progress bar shows both the percentage and the current stage label. The label updates as each stage completes. "Complete" is shown at 100%.
- **Estimated Time:** 20 min

---

### M6-T08 — End-to-end test: FastAPI repo `[BE]`
- **Description:** Manually run the complete 10-step demo flow (from MVP_PLAN.md section 10) against `https://github.com/tiangolo/fastapi`. Document any failures. Fix any bugs found. Verify: (1) ingestion completes in < 3 minutes; (2) "How does FastAPI handle dependency injection?" returns a cited answer; (3) architecture summary correctly identifies FastAPI; (4) API endpoint scanner finds route definitions; (5) dependency graph renders.
- **Files to modify:** fix any bugs found
- **Dependencies:** M6-T05, M6-T06, M6-T07
- **Acceptance Criteria:** All 10 demo steps from MVP_PLAN.md section 10 complete without errors on the FastAPI repo. Noted bugs are fixed before moving to the next E2E test.
- **Estimated Time:** 35 min

---

### M6-T09 — End-to-end test: Express repo `[BE]`
- **Description:** Run the full demo flow against `https://github.com/expressjs/express`. Focus on: (1) API endpoint scanner picks up Express route registrations; (2) architecture summary identifies Node.js + Express; (3) dependency graph shows module relationships; (4) file explorer shows `.js` files with correct language icons; (5) chat answers "How does Express handle middleware?" correctly. Fix any issues found.
- **Files to modify:** fix any bugs found
- **Dependencies:** M6-T08
- **Acceptance Criteria:** API endpoint scanner returns > 5 routes from the Express source. Architecture summary mentions Express and Node.js. No crashes or error states during the demo flow.
- **Estimated Time:** 30 min

---

### M6-T10 — E2E smoke test script `[BE]`
- **Description:** Create `backend/tests/test_e2e_smoke.py`. Write a pytest test that: (1) creates a project pointing at a small, fast-to-clone public repo (use a tiny test fixture or a repo with < 20 files); (2) calls `run_ingestion` directly; (3) asserts status is `ready`; (4) calls `search_service.search("main function", project_id, db)` and asserts > 0 results; (5) calls `chat_service.process_chat` with a simple question and collects the full streamed response; (6) asserts the response contains at least one `[file:` citation. Mark this test with `@pytest.mark.e2e` so it is excluded from the default test run.
- **Files to create:** `backend/tests/test_e2e_smoke.py`
- **Dependencies:** M6-T09
- **Acceptance Criteria:** `pytest -m e2e tests/test_e2e_smoke.py` passes end-to-end. The test requires valid `GEMINI_API_KEY` / `GROQ_API_KEY` in `.env` and notes this in a skip condition.
- **Estimated Time:** 30 min

---

### M6-T11 — README.md `[INFRA]`
- **Description:** Write the root `README.md`. Structure: (1) one-line description and a screenshot (placeholder for now); (2) "How it works" — 4-bullet technical overview (parse → embed → search → RAG); (3) "Tech stack" table matching MVP_PLAN.md section 4; (4) "Setup" — exactly 3 steps: clone, copy and fill `.env`, `docker-compose up`; (5) "Usage" — the 10-step demo script from MVP_PLAN.md section 10; (6) "Architecture" — include the ASCII architecture diagram from MVP_PLAN.md section 4.
- **Files to create:** `README.md`
- **Dependencies:** M6-T03
- **Acceptance Criteria:** A developer unfamiliar with the project can set it up by following only the README. The setup section has exactly 3 steps. The tech stack table is accurate.
- **Estimated Time:** 25 min

---

## Task Summary

| Milestone | Tasks | Estimated Time |
|---|---|---|
| M1 — Foundation | 22 | ~9 hours |
| M2 — Parsing + Embeddings + FAISS | 16 | ~8 hours |
| M3 — AI Chat | 13 | ~7.5 hours |
| M4 — File Explorer + Code Viewer | 8 | ~4.5 hours |
| M5 — Generation Features | 12 | ~6.5 hours |
| M6 — Docker + Polish | 11 | ~5.5 hours |
| **Total** | **82** | **~41 hours** |

> Note: 41 hours of focused work spread across 28 days is approximately 1.5 hours/day — very achievable. The remaining daily time absorbs debugging, reading docs, and re-runs.

---

## Critical Path

The tasks that block the most downstream work, in order:

1. **M1-T05** (Alembic migration) — nothing in the DB layer can be tested until this runs
2. **M2-T01** (tree-sitter setup) — all parsers depend on this; tree-sitter grammar installation is the most likely environment problem in the project
3. **M2-T09** (sentence-transformers) — model download takes 5–10 min on first run; do this early to unblock M6-T01
4. **M3-T04** (LLM fallback client) — all generation features depend on this; validate both API keys before building chat
5. **M4-T07** (CitationContext) — citation clicks do not work until this wires the chat to the code viewer

Do not begin a milestone until the tasks marked as dependencies in that milestone are confirmed passing.
