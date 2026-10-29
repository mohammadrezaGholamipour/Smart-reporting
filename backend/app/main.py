from app.api.sources import router as sources_router
from app.api.health import router as health_router
from app.api.search import router as search_router
from app.models import DataSource, ReportHistory
from app.api.chat import router as chat_router
from contextlib import asynccontextmanager
from app.store.db import Base, engine
from app.core.config import settings
from fastapi import FastAPI
from pathlib import Path



@asynccontextmanager
async def lifespan(app: FastAPI):
    Path(settings.upload_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.processed_dir).mkdir(parents=True, exist_ok=True)
    Path(settings.chroma_dir).mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    yield


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(health_router, prefix=settings.api_prefix)
app.include_router(sources_router, prefix=settings.api_prefix)
app.include_router(search_router, prefix=settings.api_prefix)
app.include_router(chat_router, prefix=settings.api_prefix)


@app.get("/")
def root():
    return {
        "app": settings.app_name,
        "status": "running",
        "docs": "/docs",
    }
