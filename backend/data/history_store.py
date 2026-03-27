"""Data Layer — SQLite-based analysis history storage.

Stores every JD analysis with:
  - Job URL, title, company
  - Full analysis results per resume
  - Timestamps for chronological browsing
  - Search by title, company, verdict
"""

import json
import sqlite3
import threading
import time
import uuid

from config import HISTORY_DB_PATH

_CREATE_SQL = """
CREATE TABLE IF NOT EXISTS analysis_history (
    id TEXT PRIMARY KEY,
    created_at REAL NOT NULL,
    job_url TEXT DEFAULT '',
    job_title TEXT DEFAULT '',
    company TEXT DEFAULT '',
    jd_snippet TEXT DEFAULT '',
    best_resume TEXT DEFAULT '',
    best_score INTEGER DEFAULT 0,
    best_verdict TEXT DEFAULT '',
    resume_count INTEGER DEFAULT 0,
    results_json TEXT NOT NULL
);

CREATE INDEX IF NOT EXISTS idx_created_at ON analysis_history(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_company ON analysis_history(company);
CREATE INDEX IF NOT EXISTS idx_verdict ON analysis_history(best_verdict);
"""


class HistoryStore:
    """Thread-safe SQLite store for analysis history."""

    def __init__(self, db_path: str = HISTORY_DB_PATH):
        self._db_path = db_path
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        with self._lock:
            conn = sqlite3.connect(self._db_path)
            conn.executescript(_CREATE_SQL)
            conn.close()

    def _conn(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self._db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def save(
        self,
        job_url: str,
        job_title: str,
        company: str,
        jd_snippet: str,
        best_resume: str,
        best_score: int,
        best_verdict: str,
        resume_count: int,
        results: list[dict],
    ) -> str:
        """Save an analysis result. Returns the history entry ID."""
        entry_id = str(uuid.uuid4())[:12]
        now = time.time()

        with self._lock:
            conn = self._conn()
            conn.execute(
                """INSERT INTO analysis_history
                   (id, created_at, job_url, job_title, company, jd_snippet,
                    best_resume, best_score, best_verdict, resume_count, results_json)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (entry_id, now, job_url, job_title, company,
                 jd_snippet[:500], best_resume, best_score, best_verdict,
                 resume_count, json.dumps(results)),
            )
            conn.commit()
            conn.close()

        return entry_id

    def list_recent(self, limit: int = 50, offset: int = 0) -> list[dict]:
        """Get recent history entries (without full results_json for speed)."""
        with self._lock:
            conn = self._conn()
            rows = conn.execute(
                """SELECT id, created_at, job_url, job_title, company,
                          best_resume, best_score, best_verdict, resume_count
                   FROM analysis_history
                   ORDER BY created_at DESC
                   LIMIT ? OFFSET ?""",
                (limit, offset),
            ).fetchall()
            conn.close()
        return [dict(r) for r in rows]

    def get_by_id(self, entry_id: str) -> dict | None:
        """Get a single history entry with full results."""
        with self._lock:
            conn = self._conn()
            row = conn.execute(
                "SELECT * FROM analysis_history WHERE id = ?", (entry_id,)
            ).fetchone()
            conn.close()
        if not row:
            return None
        entry = dict(row)
        entry["results"] = json.loads(entry.pop("results_json"))
        return entry

    def search(self, query: str, limit: int = 30) -> list[dict]:
        """Search history by job title, company, or verdict."""
        pattern = f"%{query}%"
        with self._lock:
            conn = self._conn()
            rows = conn.execute(
                """SELECT id, created_at, job_url, job_title, company,
                          best_resume, best_score, best_verdict, resume_count
                   FROM analysis_history
                   WHERE job_title LIKE ? OR company LIKE ? OR best_verdict LIKE ?
                         OR best_resume LIKE ?
                   ORDER BY created_at DESC
                   LIMIT ?""",
                (pattern, pattern, pattern, pattern, limit),
            ).fetchall()
            conn.close()
        return [dict(r) for r in rows]

    def delete(self, entry_id: str) -> bool:
        with self._lock:
            conn = self._conn()
            cursor = conn.execute("DELETE FROM analysis_history WHERE id = ?", (entry_id,))
            conn.commit()
            deleted = cursor.rowcount > 0
            conn.close()
        return deleted

    def count(self) -> int:
        with self._lock:
            conn = self._conn()
            row = conn.execute("SELECT COUNT(*) as cnt FROM analysis_history").fetchone()
            conn.close()
        return row["cnt"]


# Singleton
history_store = HistoryStore()
