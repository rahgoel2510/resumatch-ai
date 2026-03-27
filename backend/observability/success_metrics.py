"""Observability — success measurement KPIs.

Tracks key performance indicators for the RAG pipeline:
  1. Analysis quality — ATS accuracy, confidence distribution
  2. Pipeline health — latency percentiles, error rates
  3. User satisfaction — feedback positive rate, apply-through rate
  4. Governance compliance — violation rate, approval distribution
"""

import threading
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class AnalysisKPI:
    """KPIs captured per analysis request."""
    request_id: str = ""
    latency_ms: float = 0.0
    confidence: float = 0.0
    best_score: int = 0
    used_fallback: bool = False
    guardrail_violations: int = 0
    pii_redacted: int = 0
    governance_status: str = "approved"
    chunks_retrieved: int = 0
    resume_count: int = 0


class SuccessTracker:
    """Aggregates KPIs into dashboard-ready metrics."""

    def __init__(self, window_size: int = 200):
        self._kpis: list[AnalysisKPI] = []
        self._max = window_size
        self._lock = threading.Lock()
        self._totals = defaultdict(float)
        self._counts = defaultdict(int)

    def record(self, kpi: AnalysisKPI):
        with self._lock:
            self._kpis.append(kpi)
            if len(self._kpis) > self._max:
                self._kpis = self._kpis[-self._max:]

            self._counts["total"] += 1
            self._totals["latency"] += kpi.latency_ms
            self._totals["confidence"] += kpi.confidence
            self._totals["best_score"] += kpi.best_score
            if kpi.used_fallback:
                self._counts["fallbacks"] += 1
            if kpi.guardrail_violations > 0:
                self._counts["with_violations"] += 1
            if kpi.pii_redacted > 0:
                self._counts["with_pii"] += 1
            self._counts[f"gov_{kpi.governance_status}"] += 1

    def get_dashboard(self) -> dict:
        """Get a full KPI dashboard."""
        with self._lock:
            total = self._counts["total"]
            if total == 0:
                return {"total_analyses": 0, "status": "no data"}

            recent = self._kpis[-50:]
            latencies = sorted(k.latency_ms for k in recent)
            confidences = [k.confidence for k in recent]
            scores = [k.best_score for k in recent]

            return {
                "total_analyses": total,

                # Latency
                "latency_avg_ms": round(self._totals["latency"] / total, 1),
                "latency_p50_ms": round(latencies[len(latencies) // 2], 1) if latencies else 0,
                "latency_p95_ms": round(latencies[int(len(latencies) * 0.95)], 1) if latencies else 0,
                "latency_p99_ms": round(latencies[int(len(latencies) * 0.99)], 1) if latencies else 0,

                # Quality
                "avg_confidence": round(sum(confidences) / len(confidences), 3) if confidences else 0,
                "avg_best_score": round(sum(scores) / len(scores), 1) if scores else 0,
                "fallback_rate_pct": round(self._counts["fallbacks"] / total * 100, 1),

                # Governance
                "governance_approved_pct": round(self._counts.get("gov_approved", 0) / total * 100, 1),
                "governance_flagged_pct": round(self._counts.get("gov_flagged_for_review", 0) / total * 100, 1),
                "governance_blocked_pct": round(self._counts.get("gov_blocked", 0) / total * 100, 1),

                # Safety
                "pii_detection_rate_pct": round(self._counts["with_pii"] / total * 100, 1),
                "guardrail_violation_rate_pct": round(self._counts["with_violations"] / total * 100, 1),
            }


# Singleton
success_tracker = SuccessTracker()
