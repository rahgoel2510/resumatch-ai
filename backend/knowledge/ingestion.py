"""Knowledge Layer — document ingestion, chunking, metadata tagging.

Pipeline:
  1. Extract text from PDF/TXT (via ResumeRepository)
  2. Redact PII before embedding
  3. Detect resume sections (summary, experience, skills, education)
  4. Chunk with metadata: section, recency, RBAC tags
  5. Return enriched Document objects ready for vector embedding
"""

from langchain.schema import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

from config import CHUNK_SIZE, CHUNK_OVERLAP
from knowledge.pii_redactor import redact_pii, RedactionResult
from knowledge.access_control import create_access_tag, AccessTag
from ats_scorer import (
    _extract_section,
    _SUMMARY_PATTERNS, _EXPERIENCE_PATTERNS,
    _SKILLS_PATTERNS, _EDUCATION_PATTERNS,
)
from observability.metrics import metrics_collector


_SECTIONS = [
    ("summary", _SUMMARY_PATTERNS),
    ("experience", _EXPERIENCE_PATTERNS),
    ("skills", _SKILLS_PATTERNS),
    ("education", _EDUCATION_PATTERNS),
]

_splitter = RecursiveCharacterTextSplitter(
    chunk_size=CHUNK_SIZE, chunk_overlap=CHUNK_OVERLAP,
)


class IngestionResult:
    """Result of ingesting a single document."""

    def __init__(
        self,
        filename: str,
        original_text: str,
        clean_text: str,
        chunks: list[Document],
        pii_result: RedactionResult,
        access_tag: AccessTag,
    ):
        self.filename = filename
        self.original_text = original_text
        self.clean_text = clean_text
        self.chunks = chunks
        self.pii_result = pii_result
        self.access_tag = access_tag

    @property
    def chunk_count(self) -> int:
        return len(self.chunks)

    @property
    def pii_count(self) -> int:
        return self.pii_result.redaction_count


def ingest_document(
    filename: str,
    raw_text: str,
    namespace: str = "default",
    owner: str = "default",
) -> IngestionResult:
    """
    Full ingestion pipeline for a single resume document.

    Steps:
      1. PII redaction
      2. RBAC tag creation
      3. Section detection + metadata-enriched chunking
    """
    # 1. PII redaction — clean text before it enters the embedding space
    pii_result = redact_pii(raw_text)
    clean_text = pii_result.clean_text

    if pii_result.had_pii:
        pii_types = set(d.pii_type for d in pii_result.detections)
        print(f"  [Ingestion] PII redacted from {filename}: {pii_result.redaction_count} items ({', '.join(pii_types)})")

    # 2. RBAC tag
    access_tag = create_access_tag(
        namespace=namespace,
        owner=owner,
        document_text=raw_text,
    )
    rbac_meta = access_tag.to_metadata()

    # 3. Section-aware chunking with metadata
    chunks = _build_enriched_chunks(clean_text, filename, rbac_meta)

    print(f"  [Ingestion] {filename}: {len(chunks)} chunks, {pii_result.redaction_count} PII redacted")

    return IngestionResult(
        filename=filename,
        original_text=raw_text,
        clean_text=clean_text,
        chunks=chunks,
        pii_result=pii_result,
        access_tag=access_tag,
    )


def _build_enriched_chunks(
    clean_text: str,
    filename: str,
    rbac_meta: dict,
) -> list[Document]:
    """Build chunks with section + recency + RBAC metadata."""
    all_chunks = []
    used_text = set()

    for section_name, patterns in _SECTIONS:
        section_text = _extract_section(clean_text, patterns)
        if not section_text or section_text in used_text:
            continue
        used_text.add(section_text)

        prefix = f"[{section_name.upper()}] "
        raw_chunks = _splitter.split_text(section_text)

        for i, chunk in enumerate(raw_chunks):
            recency = "recent" if (section_name == "experience" and i < 3) else "older"
            metadata = {
                "source": filename,
                "section": section_name,
                "recency": recency,
                "chunk_index": i,
                **rbac_meta,
            }
            all_chunks.append(Document(
                page_content=prefix + chunk,
                metadata=metadata,
            ))

    # Fallback: if section detection missed content
    if not all_chunks:
        raw_chunks = _splitter.split_text(clean_text)
        for i, chunk in enumerate(raw_chunks):
            metadata = {
                "source": filename,
                "section": "unknown",
                "recency": "unknown",
                "chunk_index": i,
                **rbac_meta,
            }
            all_chunks.append(Document(
                page_content=chunk,
                metadata=metadata,
            ))

    return all_chunks
