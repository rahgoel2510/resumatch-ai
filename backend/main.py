"""
Entry point — wires the refined 3-layer RAG architecture.

┌──────────────────────────────────────────────────────────────────┐
│  PRESENTATION (presentation/)                                    │
│  FastAPI routes, Pydantic schemas, HTTP concerns                 │
├──────────────────────────────────────────────────────────────────┤
│  SERVICES (services/)                                            │
│  Analysis orchestration, JD cleaning, LLM inference              │
├──────────────────────────────────────────────────────────────────┤
│  A) KNOWLEDGE LAYER (knowledge/)                                 │
│     Document ingestion, PII redaction, RBAC tagging              │
│                                                                  │
│  B) RETRIEVAL LAYER (retrieval/)                                 │
│     Vector store + namespace isolation, query sanitization,      │
│     top-k retrieval with access control + domain filters         │
│                                                                  │
│  C) VALIDATION LAYER (validation/)                               │
│     Guardrails (PII + policy), confidence scoring + fallback,    │
│     output sanitization, audit logging + anomaly detection       │
├──────────────────────────────────────────────────────────────────┤
│  OBSERVABILITY (observability/)                                  │
│  Metrics tracking, feedback loop, anomaly detection              │
├──────────────────────────────────────────────────────────────────┤
│  DATA ACCESS (data/)                                             │
│  Model loading, resume file I/O                                  │
└──────────────────────────────────────────────────────────────────┘
"""

from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from config import HOST, PORT
from services.analysis_service import AnalysisService
from presentation.routes import router, set_service

analysis_service = AnalysisService()


@asynccontextmanager
async def lifespan(app: FastAPI):
    analysis_service.initialize()
    set_service(analysis_service)
    yield


app = FastAPI(
    title="Job Analyzer RAG API",
    description="Refined 3-layer local RAG pipeline with guardrails, RBAC, and observability",
    version="3.0.0",
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
