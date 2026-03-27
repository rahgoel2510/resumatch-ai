"""Business Logic Layer — Job description boilerplate cleaning."""

import re

# Patterns that mark the start of boilerplate sections
_CUT_MARKERS = [
    r"(?i)\b(our benefits|what we offer|perks and benefits|benefits:)",
    r"(?i)\b(equal employment opportunity|commitment to diversity|EEO)",
    r"(?i)\b(paypal does not charge|recruitment fraud|report it immediately)",
    r"(?i)\b(who we are|about the company|about us)\s*[:.]",
    r"(?i)\b(the company)\s*\n",
    r"(?i)\b(subsidiary|travel percent)",
    r"(?i)\b(disclaimer|privacy policy|cookie policy)",
]


def clean_job_description(raw_jd: str) -> str:
    """Strip company boilerplate from a job description to isolate requirements."""
    text = raw_jd
    for pattern in _CUT_MARKERS:
        match = re.search(pattern, text)
        if match:
            candidate = text[:match.start()].strip()
            if len(candidate) > 200:
                text = candidate
    return text.strip()
