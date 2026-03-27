"""Observability — metrics tracking for retrieval precision, latency, guardrail violations."""

import time
import threading
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class RequestMetrics:
    """Metrics for a single analysis request."""
    request_id: str
    timestamp: float
    latency_ms: float = 0.0
    retrieval_latency_ms: float = 0.0
    llm_latency_ms: float = 0.0
    ats_latency_ms: float = 0.0
    chunks_retrieved: int = 0
    pii_detections: int = 0
    pii_redactions: int = 0
    guardrail_violations: list[str] = field(default_factory=list)
    confidence_score: float = 0.0
    used_fallback: bool = False
    query_sanitized: bool = False
    output_sanitized: bool = False
    resume_count: int = 0


class MetricsCollector:
    """Thread-safe metrics collector with rolling window."""

    def __init__(self, max_history: int = 500):
        self._history: list[RequestMetrics] = []
        self._max = max_history
        self._lock = threading.Lock()
        self._counters = defaultdict(int)
        self._violation_counts = defaultdict(int)

    def record(self, metrics: RequestMetrics):
        with self._lock:
            self._history.append(metrics)
            if len(self._history) > self._max:
                self._history = self._history[-self._max:]
            self._counters["total_requests"] += 1
            if metrics.used_fallback:
                self._counters["fallback_used"] += 1
            if metrics.pii_detections > 0:
                self._counters["pii_detected"] += metrics.pii_detections
            for v in metrics.guardrail_violations:
                self._violation_counts[v] += 1

    def get_summary(self) -> dict:
        with self._lock:
            if not self._history:
                return {"total_requests": 0}

            recent = self._history[-50:]
            avg_latency = sum(m.latency_ms for m in recent) / len(recent)
            avg_retrieval = sum(m.retrieval_latency_ms for m in recent) / len(recent)
            avg_confidence = sum(m.confidence_score for m in recent) / len(recent)

            return {
                "total_requests": self._counters["total_requests"],
                "avg_latency_ms": round(avg_latency, 1),
                "avg_retrieval_latency_ms": round(avg_retrieval, 1),
                "avg_confidence": round(avg_confidence, 3),
                "total_pii_detected": self._counters["pii_detected"],
                "total_fallbacks": self._counters["fallback_used"],
                "guardrail_violations": dict(self._violation_counts),
                "recent_requests": len(recent),
            }


class Timer:
    """Context manager for timing code blocks."""

    def __init__(self):
        self.elapsed_ms = 0.0

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        self.elapsed_ms = (time.perf_counter() - self._start) * 1000


# Singleton
metrics_collector = MetricsCollector()
