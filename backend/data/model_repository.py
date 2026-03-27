"""Data Layer — HuggingFace model loading and caching."""

import os
from langchain_huggingface import HuggingFaceEmbeddings
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM, pipeline as hf_pipeline
from config import EMBEDDING_MODEL, LLM_MODEL, MODEL_CACHE_DIR


class ModelRepository:
    """Loads and caches HuggingFace models locally."""

    def __init__(self):
        self._embeddings = None
        self._llm_pipeline = None

    def load_all(self):
        """Download (if needed) and load both models."""
        os.makedirs(MODEL_CACHE_DIR, exist_ok=True)
        self._load_embeddings()
        self._load_llm()

    def _load_embeddings(self):
        print(f"[ModelRepo] Loading embedding model → {MODEL_CACHE_DIR}")
        self._embeddings = HuggingFaceEmbeddings(
            model_name=EMBEDDING_MODEL,
            cache_folder=MODEL_CACHE_DIR,
            model_kwargs={"device": "cpu"},
        )

    def _load_llm(self):
        print(f"[ModelRepo] Loading LLM → {MODEL_CACHE_DIR}")
        tokenizer = AutoTokenizer.from_pretrained(LLM_MODEL, cache_dir=MODEL_CACHE_DIR)
        model = AutoModelForSeq2SeqLM.from_pretrained(LLM_MODEL, cache_dir=MODEL_CACHE_DIR)
        self._llm_pipeline = hf_pipeline(
            "text2text-generation",
            model=model,
            tokenizer=tokenizer,
            max_new_tokens=512,
            do_sample=False,
        )

    @property
    def embeddings(self) -> HuggingFaceEmbeddings:
        if self._embeddings is None:
            raise RuntimeError("Models not loaded. Call load_all() first.")
        return self._embeddings

    @property
    def llm_pipeline(self):
        if self._llm_pipeline is None:
            raise RuntimeError("Models not loaded. Call load_all() first.")
        return self._llm_pipeline
