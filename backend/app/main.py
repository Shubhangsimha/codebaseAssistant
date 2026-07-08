import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.ingestion.router import router as ingestion_router
from app.projects.router import router as projects_router

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
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(projects_router, prefix="/projects", tags=["projects"])
app.include_router(ingestion_router, prefix="/projects", tags=["ingestion"])


@app.on_event("startup")
async def on_startup() -> None:
    logger.info("CodeSage API starting up")


@app.get("/health", tags=["meta"])
async def health() -> dict[str, str]:
    return {"status": "ok"}
