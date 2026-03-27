"""Validation Layer — confidence scoring + fallback to rule-based workflow.

Computes a confidence score for the analysis result. If confidence is
below threshold, falls back to a deterministic rule-based assessment
instead of relying on the LLM output.
"""

from dataclasses import dataclass


@dataclass
class ConfidenceResult:
    """Confidence assessment of an analysis."""
    score: float              # 0.0 - 1.0
    used_fallback: bool
    reason: str
    llm_output: str           # final output (LLM or fallback)


# Thresholds
CONFIDENCE_THRESHOLD = 0.35   # below this → use rule-based fallback
MIN_LLM_OUTPUT_LENGTH = 15    # LLM outputs shorter than this are unreliable


def assess_confidence(
    ats_score: int,
    semantic_score: float,
    combined_score: int,
    llm_output: str,
    chunks_retrieved: int,
    missing_keywords: list[str],
    matched_keywords: list[str],
    verdict: str,
    quantification_score: int,
) -> ConfidenceResult:
    """
    Compute confidence in the analysis result.

    Factors:
      - LLM output quality (length, coherence)
      - Number of chunks retrieved (more = better context)
      - Keyword match ratio
      - Score spread (very low or very high = more confident)
    """
    signals = []

    # LLM output quality
    llm_len = len(llm_output.strip())
    if llm_len >= 100:
        signals.append(0.3)
    elif llm_len >= 50:
        signals.append(0.2)
    elif llm_len >= MIN_LLM_OUTPUT_LENGTH:
        signals.append(0.1)
    else:
        signals.append(0.0)

    # Retrieval quality
    if chunks_retrieved >= 3:
        signals.append(0.25)
    elif chunks_retrieved >= 1:
        signals.append(0.15)
    else:
        signals.append(0.0)

    # Keyword coverage
    total_kw = len(matched_keywords) + len(missing_keywords)
    if total_kw > 0:
        match_ratio = len(matched_keywords) / total_kw
        signals.append(match_ratio * 0.25)
    else:
        signals.append(0.0)

    # Score decisiveness (extreme scores = more confident)
    if combined_score >= 70 or combined_score <= 25:
        signals.append(0.2)
    elif combined_score >= 55 or combined_score <= 35:
        signals.append(0.1)
    else:
        signals.append(0.05)  # middle ground = less confident

    confidence = min(sum(signals), 1.0)

    # Decide: use LLM or fallback
    if confidence < CONFIDENCE_THRESHOLD or llm_len < MIN_LLM_OUTPUT_LENGTH:
        fallback = _rule_based_analysis(
            ats_score, semantic_score, combined_score,
            missing_keywords, verdict, quantification_score,
        )
        return ConfidenceResult(
            score=confidence,
            used_fallback=True,
            reason=f"Low confidence ({confidence:.2f}) — using rule-based analysis",
            llm_output=fallback,
        )

    return ConfidenceResult(
        score=confidence,
        used_fallback=False,
        reason=f"Confidence: {confidence:.2f}",
        llm_output=llm_output,
    )


def _rule_based_analysis(
    ats_score: int,
    semantic_score: float,
    combined_score: int,
    missing_keywords: list[str],
    verdict: str,
    quantification_score: int,
) -> str:
    """Deterministic fallback when LLM confidence is low."""
    missing_str = ", ".join(missing_keywords[:5]) or "none"
    quant_note = (
        f"Resume has strong quantified achievements ({quantification_score}/15)."
        if quantification_score >= 10
        else f"Consider adding more quantified results to your resume ({quantification_score}/15)."
    )

    return (
        f"ATS Score: {ats_score}% | Semantic Fit: {semantic_score}% | "
        f"Combined: {combined_score}%. "
        f"Key gaps: {missing_str}. "
        f"{quant_note} "
        f"Verdict: {verdict}."
    )
