"""Knowledge Layer — PII detection and redaction before embedding.

Detects and redacts personally identifiable information from resume text
BEFORE it gets chunked and embedded into the vector store. This ensures
PII never enters the embedding space.

Detected PII types:
  - Email addresses
  - Phone numbers (US/IN/international formats)
  - Social Security Numbers
  - Credit card numbers
  - Physical addresses (partial — street patterns)
  - URLs with personal identifiers
  - Aadhaar numbers (India)
  - PAN numbers (India)
"""

import re
from dataclasses import dataclass, field


@dataclass
class PIIDetection:
    """A single PII detection."""
    pii_type: str
    original: str
    start: int
    end: int


@dataclass
class RedactionResult:
    """Result of PII redaction on a text."""
    clean_text: str
    detections: list[PIIDetection] = field(default_factory=list)
    redaction_count: int = 0

    @property
    def had_pii(self) -> bool:
        return self.redaction_count > 0


# Ordered patterns — more specific first to avoid partial matches
_PII_PATTERNS: list[tuple[str, str, str]] = [
    # (name, regex, replacement)
    ("ssn", r"\b\d{3}-\d{2}-\d{4}\b", "[SSN_REDACTED]"),
    ("aadhaar", r"\b\d{4}\s?\d{4}\s?\d{4}\b", "[AADHAAR_REDACTED]"),
    ("pan", r"\b[A-Z]{5}\d{4}[A-Z]\b", "[PAN_REDACTED]"),
    ("credit_card", r"\b(?:\d{4}[-\s]?){3}\d{4}\b", "[CC_REDACTED]"),
    ("email", r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b", "[EMAIL_REDACTED]"),
    ("phone", r"(?:\+?\d{1,3}[-.\s]?)?\(?\d{2,4}\)?[-.\s]?\d{3,4}[-.\s]?\d{3,4}\b", "[PHONE_REDACTED]"),
    ("url_personal", r"https?://(?:www\.)?linkedin\.com/in/[A-Za-z0-9_-]+", "[LINKEDIN_REDACTED]"),
    ("url_personal", r"https?://(?:www\.)?github\.com/[A-Za-z0-9_-]+", "[GITHUB_REDACTED]"),
    ("address", r"\b\d{1,5}\s+[A-Z][a-z]+(?:\s+[A-Z][a-z]+)*\s+(?:St|Ave|Blvd|Dr|Rd|Ln|Way|Ct|Pl)\b\.?", "[ADDRESS_REDACTED]"),
]

# Patterns that should NOT be redacted (false positives)
_WHITELIST_PATTERNS = [
    r"\b\d{4}\b",           # plain 4-digit numbers (years, etc.)
    r"\b\d{1,2}/\d{4}\b",   # date formats like 01/2024
]


def detect_pii(text: str) -> list[PIIDetection]:
    """Detect PII in text without modifying it."""
    detections = []
    for pii_type, pattern, _ in _PII_PATTERNS:
        for match in re.finditer(pattern, text):
            # Skip if it's a whitelisted pattern
            matched_text = match.group()
            is_whitelisted = any(
                re.fullmatch(wp, matched_text) for wp in _WHITELIST_PATTERNS
            )
            if is_whitelisted:
                continue
            detections.append(PIIDetection(
                pii_type=pii_type,
                original=matched_text,
                start=match.start(),
                end=match.end(),
            ))
    return detections


def redact_pii(text: str) -> RedactionResult:
    """Detect and redact all PII from text. Returns clean text + detection log."""
    detections = detect_pii(text)
    if not detections:
        return RedactionResult(clean_text=text, detections=[], redaction_count=0)

    # Sort by position descending so replacements don't shift offsets
    detections.sort(key=lambda d: d.start, reverse=True)

    clean = text
    replacement_map = {pii_type: repl for pii_type, _, repl in _PII_PATTERNS}

    for det in detections:
        replacement = replacement_map.get(det.pii_type, "[PII_REDACTED]")
        clean = clean[:det.start] + replacement + clean[det.end:]

    return RedactionResult(
        clean_text=clean,
        detections=list(reversed(detections)),  # restore original order
        redaction_count=len(detections),
    )
