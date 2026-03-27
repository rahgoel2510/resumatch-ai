"""Observability — feedback loop for continuous improvement."""

import json
import os
import time
import threading
from dataclasses import dataclass, asdict

from config import FEEDBACK_FILE

_FEEDBACK_FILE = FEEDBACK_FILE


@dataclass
class FeedbackEntry:
    """User feedback on an analysis result."""
    timestamp: float
    resume_filename: str
    verdict: str
    combined_score: int
    user_action: str          # "applied", "skipped", "thumbs_up", "thumbs_down"
    user_comment: str = ""
    jd_snippet: str = ""      # first 200 chars of JD for context


class FeedbackStore:
    """Append-only feedback log for tracking analysis quality over time."""

    def __init__(self, filepath: str = _FEEDBACK_FILE):
        self._filepath = filepath
        self._lock = threading.Lock()

    def record(self, entry: FeedbackEntry):
        with self._lock:
            with open(self._filepath, "a") as f:
                f.write(json.dumps(asdict(entry)) + "\n")

    def get_recent(self, n: int = 50) -> list[dict]:
        if not os.path.exists(self._filepath):
            return []
        with self._lock:
            with open(self._filepath, "r") as f:
                lines = f.readlines()
        entries = []
        for line in lines[-n:]:
            try:
                entries.append(json.loads(line.strip()))
            except json.JSONDecodeError:
                continue
        return entries

    def get_accuracy_stats(self) -> dict:
        """Compute accuracy metrics from feedback."""
        entries = self.get_recent(200)
        if not entries:
            return {"total_feedback": 0}

        positive = sum(1 for e in entries if e.get("user_action") in ("applied", "thumbs_up"))
        negative = sum(1 for e in entries if e.get("user_action") in ("skipped", "thumbs_down"))
        total = positive + negative

        return {
            "total_feedback": len(entries),
            "positive_rate": round(positive / total * 100, 1) if total > 0 else 0,
            "negative_rate": round(negative / total * 100, 1) if total > 0 else 0,
        }


# Singleton
feedback_store = FeedbackStore()
