"""Retrieval Layer — FAISS vector store with namespace isolation.

Each resume gets its own FAISS index (namespace isolation).
Metadata includes RBAC tags for access control enforcement at query time.
"""

import numpy as np
from dataclasses import dataclass
from langchain.schema import Document
from langchain_community.vectorstores import FAISS
from langchain_huggingface import HuggingFaceEmbeddings

from config import TOP_K_RESULTS
from knowledge.access_control import check_access


@dataclass
class NamespacedIndex:
    """A single resume's vector index within its namespace."""
    filename: str
    namespace: str
    owner: str
    text: str                # original (un-redacted) text for ATS scoring
    clean_text: str          # PII-redacted text
    vectorstore: FAISS
    chunk_count: int
    pii_redacted_count: int


class VectorStore:
    """Manages per-resume FAISS indexes with namespace isolation."""

    def __init__(self, embeddings: HuggingFaceEmbeddings):
        self._embeddings = embeddings

    def create_index(
        self,
        filename: str,
        namespace: str,
        owner: str,
        original_text: str,
        clean_text: str,
        chunks: list[Document],
        pii_count: int = 0,
    ) -> NamespacedIndex:
        """Build a FAISS index from pre-processed chunks."""
        vs = FAISS.from_documents(chunks, self._embeddings)
        return NamespacedIndex(
            filename=filename,
            namespace=namespace,
            owner=owner,
            text=original_text,
            clean_text=clean_text,
            vectorstore=vs,
            chunk_count=len(chunks),
            pii_redacted_count=pii_count,
        )

    def search(
        self,
        index: NamespacedIndex,
        query: str,
        k: int = TOP_K_RESULTS,
        requesting_namespace: str = "default",
        requesting_owner: str = "",
        domain_filter: dict | None = None,
    ) -> list[Document]:
        """Top-k retrieval with access control and optional domain filters."""
        # Over-fetch to account for access control filtering
        candidates = index.vectorstore.similarity_search(query, k=k * 3)

        results = []
        for doc in candidates:
            # Access control check
            if not check_access(doc.metadata, requesting_namespace, requesting_owner):
                continue

            # Domain filter (e.g., section="experience", recency="recent")
            if domain_filter:
                skip = False
                for key, value in domain_filter.items():
                    if doc.metadata.get(key) != value:
                        skip = True
                        break
                if skip:
                    continue

            results.append(doc)
            if len(results) >= k:
                break

        return results

    def semantic_score(
        self,
        index: NamespacedIndex,
        query: str,
        k: int = TOP_K_RESULTS,
    ) -> float:
        """Compute 0-100 semantic similarity score."""
        docs_and_scores = index.vectorstore.similarity_search_with_score(query, k=k)
        if not docs_and_scores:
            return 0.0
        distances = [score for _, score in docs_and_scores]
        avg_dist = np.mean(distances)
        similarity = max(0, 100 - avg_dist * 25)
        return round(similarity, 1)
