"""Validation Layer — audit logging + anomaly detection.

Logs every analysis request with full context for compliance and debugging.
Detects anomalies like unusual request patterns or repeated guardrail violations.
"""

import json
import os
import time
import threading
from dataclasses import dataclass, field, asdict
from collections import deque

from config import AUDIT_DIR

_AUDIT_FILE = os.path.join(AUDIT_DIR, "audit.jsonl")


@dataclass
class AuditEntry:
    """A single audit log entry."""
    timestamp: float = field(default_factory=time.time)
    request_id: str = ""
    action: str = ""                    # "analyze", "upload", "health"
    namespace: str = "default"
    resumes_analyzed: int = 0
    pii_detections: int = 0
    guardrail_violations: list[str] = field(default_factory=list)
    query_sanitized: bool = False
    output_sanitized: bool = False
    confidence_score: float = 0.0
    used_fallback: bool = False
    latency_ms: float = 0.0
    best_resume: str = ""
    best_score: int = 0
    anomaly_flags: list[str] = field(default_factory=list)


class AuditLogger:
    """Thread-safe audit logger with anomaly detection."""

    def __init__(self):
        os.makedirs(AUDIT_DIR, exist_ok=True)
        self._lock = threading.Lock()
        self._recent: deque[AuditEntry] = deque(maxlen=100)

    def log(self, entry: AuditEntry):
        """Log an audit entry and check for anomalies."""
        # Anomaly detection
        entry.anomaly_flags = self._detect_anomalies(entry)

        with self._lock:
            self._recent.append(entry)
            with open(_AUDIT_FILE, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

        if entry.anomaly_flags:
            print(f"  [AUDIT] ⚠ Anomalies detected: {entry.anomaly_flags}")

    def _detect_anomalies(self, entry: AuditEntry) -> list[str]:
        """Detect anomalous patterns in the current request."""
        flags = []

        # High PII count
        if entry.pii_detections > 10:
            flags.append("high_pii_count")

        # Guardrail violations
        if len(entry.guardrail_violations) > 2:
            flags.append("multiple_guardrail_violations")

        # Very low confidence
        if entry.confidence_score < 0.2:
            flags.append("very_low_confidence")

        # Rapid requests (rate anomaly)
        with self._lock:
            recent_timestamps = [e.timestamp for e in self._recent]
        if len(recent_timestamps) >= 10:
            window = recent_timestamps[-1] - recent_timestamps[-10]
            if window < 5.0:  # 10 requests in 5 seconds
                flags.append("rapid_request_rate")

        # Query was heavily sanitized
        if entry.query_sanitized:
            flags.append("query_required_sanitization")

        return flags

    def get_recent(self, n: int = 20) -> list[dict]:
        """Get recent audit entries."""
        with self._lock:
            entries = list(self._recent)[-n:]
        return [asdict(e) for e in entries]


# Singleton
audit_logger = AuditLogger()
