"""Retrieval Layer — query engine orchestrating sanitization, retrieval, access control."""

from langchain.schema import Document

from config import TOP_K_RESULTS
from retrieval.vector_store import VectorStore, NamespacedIndex
from retrieval.query_sanitizer import sanitize_query, SanitizedQuery
from observability.metrics import Timer


class QueryResult:
    """Result of a retrieval query."""

    def __init__(
        self,
        documents: list[Document],
        sanitized_query: SanitizedQuery,
        semantic_score: float,
        retrieval_latency_ms: float,
    ):
        self.documents = documents
        self.sanitized_query = sanitized_query
        self.semantic_score = semantic_score
        self.retrieval_latency_ms = retrieval_latency_ms

    @property
    def context(self) -> str:
        """Concatenated text from retrieved documents."""
        return "\n".join(doc.page_content for doc in self.documents)

    @property
    def chunk_count(self) -> int:
        return len(self.documents)


class QueryEngine:
    """Orchestrates the full retrieval pipeline."""

    def __init__(self, vector_store: VectorStore):
        self._store = vector_store

    def query(
        self,
        index: NamespacedIndex,
        raw_query: str,
        k: int = TOP_K_RESULTS,
        namespace: str = "default",
        owner: str = "",
        domain_filter: dict | None = None,
    ) -> QueryResult:
        """
        Full retrieval pipeline:
          1. Sanitize query
          2. Top-k retrieval with access control
          3. Compute semantic score
        """
        # 1. Sanitize
        sanitized = sanitize_query(raw_query)

        with Timer() as t:
            # 2. Retrieve with access control
            docs = self._store.search(
                index=index,
                query=sanitized.clean,
                k=k,
                requesting_namespace=namespace,
                requesting_owner=owner,
                domain_filter=domain_filter,
            )

            # 3. Semantic score
            sem_score = self._store.semantic_score(index, sanitized.clean, k=k)

        return QueryResult(
            documents=docs,
            sanitized_query=sanitized,
            semantic_score=sem_score,
            retrieval_latency_ms=t.elapsed_ms,
        )
