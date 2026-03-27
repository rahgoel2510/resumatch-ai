"""Knowledge Layer — RBAC tags and encryption metadata for documents.

Each document chunk gets tagged with access control metadata:
  - owner: who uploaded the resume
  - namespace: isolation boundary (e.g., user ID)
  - sensitivity: classification level (public, internal, confidential)
  - encrypted: whether the source was encrypted at rest

This metadata is stored alongside the vector embeddings and enforced
at query time by the Retrieval Layer.
"""

from dataclasses import dataclass, field
from enum import Enum
import hashlib
import time


class Sensitivity(str, Enum):
    PUBLIC = "public"
    INTERNAL = "internal"
    CONFIDENTIAL = "confidential"


@dataclass
class AccessTag:
    """RBAC metadata attached to every document chunk."""
    namespace: str                          # isolation boundary
    owner: str = "default"                  # who owns this document
    sensitivity: Sensitivity = Sensitivity.CONFIDENTIAL  # resumes are confidential by default
    created_at: float = field(default_factory=time.time)
    document_hash: str = ""                 # integrity check
    encrypted_at_rest: bool = False         # flag for encryption status

    def to_metadata(self) -> dict:
        """Convert to a flat dict for FAISS metadata storage."""
        return {
            "rbac_namespace": self.namespace,
            "rbac_owner": self.owner,
            "rbac_sensitivity": self.sensitivity.value,
            "rbac_created_at": self.created_at,
            "rbac_doc_hash": self.document_hash,
            "rbac_encrypted": self.encrypted_at_rest,
        }


def create_access_tag(
    namespace: str,
    owner: str = "default",
    document_text: str = "",
    sensitivity: Sensitivity = Sensitivity.CONFIDENTIAL,
) -> AccessTag:
    """Create an access tag for a document."""
    doc_hash = hashlib.sha256(document_text.encode()).hexdigest()[:16] if document_text else ""
    return AccessTag(
        namespace=namespace,
        owner=owner,
        sensitivity=sensitivity,
        document_hash=doc_hash,
    )


def check_access(metadata: dict, requesting_namespace: str, requesting_owner: str = "") -> bool:
    """Check if a request has access to a document chunk.

    Rules:
      - Namespace must match (isolation boundary)
      - If sensitivity is CONFIDENTIAL, owner must also match
      - PUBLIC and INTERNAL are accessible within the namespace
    """
    chunk_ns = metadata.get("rbac_namespace", "")
    chunk_owner = metadata.get("rbac_owner", "")
    chunk_sensitivity = metadata.get("rbac_sensitivity", "confidential")

    # Namespace isolation is always enforced
    if chunk_ns != requesting_namespace:
        return False

    # Confidential docs require owner match
    if chunk_sensitivity == "confidential" and requesting_owner:
        return chunk_owner == requesting_owner

    return True
