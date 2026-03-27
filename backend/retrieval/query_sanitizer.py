"""Retrieval Layer — query input sanitization.

Cleans and validates incoming queries (job descriptions) before they
hit the vector store. Prevents injection, removes noise, enforces limits.
"""

import re
from dataclasses import dataclass


@dataclass
class SanitizedQuery:
    """Result of query sanitization."""
    original: str
    clean: str
    was_modified: bool
    warnings: list[str]


# Max query length to prevent abuse
MAX_QUERY_LENGTH = 8000

# Patterns to strip from queries
_STRIP_PATTERNS = [
    # Script injection attempts
    r"<script[^>]*>.*?</script>",
    r"<[^>]+>",                          # HTML tags
    r"\{[^}]*\}",                        # JSON/template injection
    # Prompt injection patterns
    r"(?i)ignore\s+(?:all\s+)?previous\s+instructions?",
    r"(?i)you\s+are\s+now\s+(?:a|an)\s+",
    r"(?i)system\s*:\s*",
    r"(?i)assistant\s*:\s*",
    # Excessive whitespace / control chars
    r"[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]",
]


def sanitize_query(raw_query: str) -> SanitizedQuery:
    """Sanitize a query string for safe vector search."""
    warnings = []
    text = raw_query

    # Length check
    if len(text) > MAX_QUERY_LENGTH:
        text = text[:MAX_QUERY_LENGTH]
        warnings.append(f"Query truncated from {len(raw_query)} to {MAX_QUERY_LENGTH} chars")

    # Strip dangerous patterns
    for pattern in _STRIP_PATTERNS:
        cleaned = re.sub(pattern, " ", text, flags=re.DOTALL)
        if cleaned != text:
            warnings.append(f"Stripped pattern: {pattern[:40]}...")
            text = cleaned

    # Normalize whitespace
    text = re.sub(r"\s+", " ", text).strip()

    was_modified = text != raw_query

    return SanitizedQuery(
        original=raw_query,
        clean=text,
        was_modified=was_modified,
        warnings=warnings,
    )
