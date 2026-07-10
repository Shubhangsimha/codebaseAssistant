import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.chat.router import router as chat_router
from app.config import settings
from app.files.router import router as files_router
from app.generation.router import router as generation_router
from app.graph.router import router as graph_router
from app.ingestion.router import router as ingestion_router
from app.projects.router import router as projects_router
from app.search.router import router as search_router

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s  %(levelname)-8s  %(name)s  %(message)s",
)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="CodeSage API",
    description="AI Developer Intelligence Platform",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(ingestion_router, prefix="/projects", tags=["ingestion"])
app.include_router(search_router, prefix="/projects", tags=["search"])
app.include_router(chat_router, prefix="/projects", tags=["chat"])
app.include_router(files_router, prefix="/projects", tags=["files"])
app.include_router(generation_router, prefix="/projects", tags=["generation"])
app.include_router(graph_router, prefix="/projects", tags=["graph"])


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("CodeSage API starting up")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
