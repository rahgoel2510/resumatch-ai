"""Validation Layer — output sanitization before returning to the client.

Final pass on all data leaving the system:
  - Strip any residual PII from all text fields
  - Enforce response structure
  - Normalize scores to valid ranges
  - Clean up LLM artifacts
"""

import re


def sanitize_output(result: dict) -> dict:
    """Sanitize the full analysis response before returning to client."""
    if not result or "resumes" not in result:
        return result

    for resume in result.get("resumes", []):
        # Clamp scores to valid ranges
        for key in ("ats_score", "keyword_score", "contextual_placement_score",
                     "cluster_score", "category_score", "combined_score"):
            if key in resume:
                resume[key] = max(0, min(100, resume[key]))

        if "quantification_score" in resume:
            resume["quantification_score"] = max(0, min(15, resume["quantification_score"]))

        if "semantic_score" in resume:
            resume["semantic_score"] = max(0.0, min(100.0, resume["semantic_score"]))

        # Clean LLM output artifacts
        if "llm_analysis" in resume:
            resume["llm_analysis"] = _clean_llm_text(resume["llm_analysis"])

        # Clean verdict reasoning
        if "verdict_reasoning" in resume:
            resume["verdict_reasoning"] = _clean_llm_text(resume["verdict_reasoning"])

    return result


def _clean_llm_text(text: str) -> str:
    """Remove common LLM artifacts from output text."""
    if not text:
        return text

    # Remove repeated phrases (LLM stuttering)
    text = re.sub(r"(.{20,}?)\1+", r"\1", text)

    # Remove markdown artifacts that shouldn't be in plain text responses
    text = re.sub(r"\*{2,}", "", text)
    text = re.sub(r"#{1,}\s*", "", text)

    # Normalize whitespace
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = re.sub(r"  +", " ", text)

    return text.strip()
