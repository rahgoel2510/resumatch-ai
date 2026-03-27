"""
ResuMatch AI — Entry point.

Starts the FastAPI server with:
  - Full 3-layer RAG pipeline initialization
  - Background file watcher on resume_data/ (auto re-indexes on changes)
  - Cross-platform background service support (macOS launchd / Windows NSSM)
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
from services.analysis_service import AnalysisService
from services.resume_watcher import ResumeWatcher
from presentation.routes import router, set_service

analysis_service = AnalysisService()
resume_watcher = ResumeWatcher(
    rebuild_callback=analysis_service.rebuild_indexes,
    debounce_seconds=3.0,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    analysis_service.initialize()
    set_service(analysis_service)
    resume_watcher.start()
    yield
    resume_watcher.stop()


app = FastAPI(
    title="ResuMatch AI",
    description="Local RAG pipeline for resume-to-JD matching with auto-reindexing",
    version="3.1.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(router)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host=HOST, port=PORT, reload=False)
