"""Configuration for the RAG pipeline."""

import os

_BASE_DIR = os.path.dirname(__file__)

# --- Model cache ---
MODEL_CACHE_DIR = os.path.join(_BASE_DIR, "models")

# HuggingFace models (all run locally, no API keys needed)
EMBEDDING_MODEL = "sentence-transformers/all-MiniLM-L6-v2"
LLM_MODEL = "google/flan-t5-base"

# RAG settings
CHUNK_SIZE = 500
CHUNK_OVERLAP = 50
TOP_K_RESULTS = 3

# Server
HOST = "0.0.0.0"
PORT = 8000

# Resume storage
RESUME_DIR = os.path.join(_BASE_DIR, "resume_data")
ALLOWED_RESUME_EXTENSIONS = {".pdf", ".txt"}

# Observability storage
AUDIT_DIR = os.path.join(_BASE_DIR, "audit_logs")
FEEDBACK_FILE = os.path.join(_BASE_DIR, "feedback_log.jsonl")

# Governance
GOVERNANCE_CONFIG_FILE = os.path.join(_BASE_DIR, "governance.json")

# History
HISTORY_DB_PATH = os.path.join(_BASE_DIR, "history.db")
