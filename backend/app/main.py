
import sys
from pathlib import Path
from contextlib import asynccontextmanager

# Add backend directory to Python path for Vercel
BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.api.search import router as search_router
from app.api.sources import router as sources_router

from app.core.config import settings
from app.store.db import Base, engine

import app.models  # noqa: F401 - Register models for create_all


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Create required directories
    for directory in (
        settings.upload_dir,
        settings.processed_dir,
        settings.chroma_dir,
    ):
        Path(directory).mkdir(parents=True, exist_ok=True)

    # Create database tables
    Base.metadata.create_all(bind=engine)

    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

# CORS configuration
origins = [
    origin.strip()
    for origin in settings.cors_origins.split(",")
    if origin.strip()
]

allow_all_origins = not origins or "*" in origins

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"] if allow_all_origins else origins,
    allow_credentials=not allow_all_origins,
    allow_methods=["*"],
    allow_headers=["*"],
)

# API routes
app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(sources_router, prefix=settings.api_prefix)
app.include_router(search_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }
