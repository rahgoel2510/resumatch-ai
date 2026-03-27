"""Data Layer — Resume file I/O and PDF text extraction."""

import logging
import os
import shutil
from dataclasses import dataclass

from config import RESUME_DIR, ALLOWED_RESUME_EXTENSIONS


@dataclass
class ResumeDocument:
    """Raw resume data loaded from disk."""
    filename: str
    text: str


class ResumeRepository:
    """Handles reading/writing resume files from the resume_data/ directory."""

    def __init__(self, resume_dir: str = RESUME_DIR):
        self._dir = resume_dir
        os.makedirs(self._dir, exist_ok=True)

    def list_all(self) -> list[ResumeDocument]:
        """Load all resume files and return extracted text."""
        documents = []
        for filename in sorted(os.listdir(self._dir)):
            filepath = os.path.join(self._dir, filename)
            ext = os.path.splitext(filename)[1].lower()

            if ext == ".pdf":
                text = self._extract_pdf(filepath)
            elif ext == ".txt":
                with open(filepath, "r") as f:
                    text = f.read()
            else:
                continue

            if not text.strip():
                print(f"  [ResumeRepo] Skipped (empty): {filename}")
                continue

            documents.append(ResumeDocument(filename=filename, text=text))
            print(f"  [ResumeRepo] Loaded: {filename} ({len(text)} chars)")

        return documents

    def save(self, filename: str, file_obj) -> str:
        """Save an uploaded file to the resume directory."""
        ext = os.path.splitext(filename)[1].lower()
        if ext not in ALLOWED_RESUME_EXTENSIONS:
            raise ValueError(f"Unsupported file type '{ext}'. Use .pdf or .txt")

        dest = os.path.join(self._dir, filename)
        with open(dest, "wb") as f:
            shutil.copyfileobj(file_obj, f)
        return dest

    @staticmethod
    def _extract_pdf(filepath: str) -> str:
        """Extract text from a PDF file."""
        logging.getLogger("pypdf").setLevel(logging.ERROR)
        from pypdf import PdfReader
        reader = PdfReader(filepath)
        pages = []
        for page in reader.pages:
            text = page.extract_text()
            if text:
                pages.append(text)
        return "\n\n".join(pages)
