from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.reports import router as reports_router
from app.api.search import router as search_router
from app.api.sources import router as sources_router
from app.core.config import settings
from app.store.db import Base, engine

import app.models  # noqa: F401  (ثبت مدل‌ها برای create_all)


import sys
from pathlib import Path

BACKEND_DIR = Path(__file__).resolve().parents[1]

if str(BACKEND_DIR) not in sys.path:
    sys.path.insert(0, str(BACKEND_DIR))

@asynccontextmanager
async def lifespan(app: FastAPI):
    for directory in (settings.upload_dir, settings.processed_dir, settings.chroma_dir):
        Path(directory).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=origins != ["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(sources_router, prefix=settings.api_prefix)
app.include_router(search_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)
app.include_router(reports_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {"app": settings.app_name, "status": "running", "docs": "/docs"}
