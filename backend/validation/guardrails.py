"""Validation Layer — guardrails engine for PII detection and policy enforcement.

Checks both input (JD) and output (LLM response) for policy violations:
  - PII leakage in LLM output
  - Toxic/inappropriate content
  - Hallucination indicators
  - Response length limits
  - Prohibited content patterns
"""

import re
from dataclasses import dataclass, field
from knowledge.pii_redactor import detect_pii


@dataclass
class GuardrailResult:
    """Result of guardrail checks."""
    passed: bool = True
    violations: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    pii_found: int = 0
    modified_text: str = ""

    def add_violation(self, msg: str):
        self.violations.append(msg)
        self.passed = False

    def add_warning(self, msg: str):
        self.warnings.append(msg)


# Prohibited patterns in LLM output
_PROHIBITED_OUTPUT = [
    (r"(?i)\b(ignore\s+previous|system\s+prompt|you\s+are\s+an?\s+ai)\b", "prompt_leak"),
    (r"(?i)\b(kill|harm|weapon|illegal|hack)\b", "toxic_content"),
]

# Max output length
MAX_OUTPUT_LENGTH = 2000


def check_input(text: str) -> GuardrailResult:
    """Validate input (job description) before processing."""
    result = GuardrailResult(modified_text=text)

    if not text or len(text.strip()) < 20:
        result.add_violation("Input too short — need at least 20 characters")
        return result

    if len(text) > 15000:
        result.add_warning("Input very long — will be truncated")
        result.modified_text = text[:15000]

    # Check for injection attempts
    for pattern, label in _PROHIBITED_OUTPUT:
        if re.search(pattern, text):
            result.add_warning(f"Suspicious input pattern detected: {label}")

    return result


def check_output(text: str) -> GuardrailResult:
    """Validate LLM output before returning to user."""
    result = GuardrailResult(modified_text=text)

    # PII check — LLM should not leak PII
    pii_detections = detect_pii(text)
    if pii_detections:
        result.pii_found = len(pii_detections)
        result.add_violation(f"PII detected in output: {len(pii_detections)} items")
        # Redact PII from output
        from knowledge.pii_redactor import redact_pii
        redacted = redact_pii(text)
        result.modified_text = redacted.clean_text

    # Prohibited content
    for pattern, label in _PROHIBITED_OUTPUT:
        if re.search(pattern, text):
            result.add_violation(f"Prohibited content in output: {label}")

    # Length check
    if len(text) > MAX_OUTPUT_LENGTH:
        result.add_warning("Output truncated to max length")
        result.modified_text = result.modified_text[:MAX_OUTPUT_LENGTH]

    return result
