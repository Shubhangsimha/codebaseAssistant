# CodeSage

AI Developer Intelligence Platform — ask any question about a codebase in plain English.

## Setup (3 steps)

```bash
git clone https://github.com/ShubhangSimha/codebaseAssistant
cd codebaseAssistant
cp .env.example .env          # add your API keys (see below)
docker-compose up --build
```

Open **http://localhost:3000**

## API Keys (free tier, no credit card)

| Key | Where to get it | Free limit |
|-----|----------------|------------|
| `GEMINI_API_KEY` | [aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey) | 15 RPM · 1M tokens/day |
| `GROQ_API_KEY`   | [console.groq.com/keys](https://console.groq.com/keys) | 30 RPM (auto-fallback) |

Edit `.env` and set both keys.

## What it does

Paste a GitHub URL → CodeSage clones the repo, parses every file with tree-sitter, embeds chunks locally (no API cost), and stores them in FAISS. Then:

- **Chat** — ask questions in plain English, get cited answers streamed token-by-token
- **Architecture Summary** — one-click tech stack + layer breakdown
- **API Endpoint Discovery** — finds all routes across Express, FastAPI, Django, Spring
- **Doc Generator** — streams a docstring for any function in the codebase
- **Dependency Graph** — interactive import graph; circular deps highlighted red

## Tech stack

- Backend: FastAPI + SQLite + SQLAlchemy + Alembic
- Embeddings: `BAAI/bge-small-en-v1.5` via `sentence-transformers` (runs locally, no API)
- Vector store: FAISS (local, file-based)
- LLM: Gemini 2.5 Flash (primary) → Groq llama-3.1-8b (auto-fallback on rate limit)
- Frontend: Next.js 15 + TypeScript + Tailwind + shadcn/ui + React Flow

## Data persistence

SQLite and FAISS indexes are stored in a named Docker volume (`codesage_data`). They survive `docker-compose down` + `docker-compose up`.

## Development (without Docker)

```bash
# Backend
cd backend
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
cp ../.env.example ../.env   # add keys
alembic upgrade head
uvicorn app.main:app --reload

# Frontend (separate terminal)
cd frontend
npm install
npm run dev
```

## Running tests

```bash
make test
# or directly:
cd backend && pytest tests/ -v
```
