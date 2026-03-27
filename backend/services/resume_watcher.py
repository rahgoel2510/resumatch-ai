"""Background file watcher for resume_data/ directory.

Monitors the resume directory for file changes (create, modify, delete)
and triggers automatic re-ingestion + re-embedding when resumes are
added, updated, or removed.

Uses watchdog for cross-platform filesystem events (macOS + Windows + Linux).
Includes a debounce mechanism to avoid re-indexing on every partial write.
"""

import threading
import time
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler

from config import RESUME_DIR, ALLOWED_RESUME_EXTENSIONS


class _ResumeChangeHandler(FileSystemEventHandler):
    """Handles filesystem events in resume_data/ with debouncing."""

    def __init__(self, callback, debounce_seconds: float = 3.0):
        super().__init__()
        self._callback = callback
        self._debounce = debounce_seconds
        self._timer = None
        self._lock = threading.Lock()

    def _is_resume_file(self, path: str) -> bool:
        for ext in ALLOWED_RESUME_EXTENSIONS:
            if path.lower().endswith(ext):
                return True
        return False

    def _schedule_rebuild(self, event_type: str, path: str):
        if not self._is_resume_file(path):
            return
        print(f"  [Watcher] {event_type}: {path} — scheduling re-index in {self._debounce}s")
        with self._lock:
            if self._timer:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce, self._do_rebuild)
            self._timer.daemon = True
            self._timer.start()

    def _do_rebuild(self):
        print("[Watcher] Re-indexing resumes...")
        try:
            self._callback()
            print("[Watcher] Re-indexing complete.")
        except Exception as e:
            print(f"[Watcher] Re-indexing failed: {e}")

    def on_created(self, event):
        if not event.is_directory:
            self._schedule_rebuild("CREATED", event.src_path)

    def on_modified(self, event):
        if not event.is_directory:
            self._schedule_rebuild("MODIFIED", event.src_path)

    def on_deleted(self, event):
        if not event.is_directory:
            self._schedule_rebuild("DELETED", event.src_path)

    def on_moved(self, event):
        if not event.is_directory:
            self._schedule_rebuild("MOVED", event.dest_path)


class ResumeWatcher:
    """Watches resume_data/ and triggers re-indexing on changes."""

    def __init__(self, rebuild_callback, debounce_seconds: float = 3.0):
        self._callback = rebuild_callback
        self._debounce = debounce_seconds
        self._observer = None
        self._thread = None

    def start(self):
        """Start watching in a background thread."""
        handler = _ResumeChangeHandler(self._callback, self._debounce)
        self._observer = Observer()
        self._observer.schedule(handler, RESUME_DIR, recursive=False)
        self._observer.daemon = True
        self._observer.start()
        print(f"[Watcher] Monitoring {RESUME_DIR} for changes...")

    def stop(self):
        """Stop the watcher."""
        if self._observer:
            self._observer.stop()
            self._observer.join(timeout=5)
            print("[Watcher] Stopped.")
