"""Business Logic Layer — LLM inference for resume analysis."""

from data.model_repository import ModelRepository


class LLMService:
    """Generates natural-language analysis using the local LLM."""

    def __init__(self, model_repo: ModelRepository):
        self._model_repo = model_repo

    def _generate(self, prompt: str) -> str:
        return self._model_repo.llm_pipeline(prompt)[0]["generated_text"].strip()

    def analyze_resume_fit(
        self,
        resume_context: str,
        jd_text: str,
        ats_score: int,
        missing_keywords: list[str],
        verdict: str,
        semantic_score: float,
    ) -> str:
        """Generate a brief LLM assessment of resume-to-JD fit."""
        missing_str = ", ".join(missing_keywords[:5]) or "none"
        prompt = (
            f"Resume skills: {resume_context[:800]}\n\n"
            f"Job requires: {jd_text[:800]}\n\n"
            f"ATS score: {ats_score}%. Missing: {missing_str}.\n\n"
            f"Write 3 sentences: what skills match, what is missing, "
            f"and should the candidate APPLY or SKIP this job?"
        )
        result = self._generate(prompt)
        if len(result) < 20:
            result = (
                f"ATS: {ats_score}%. Semantic fit: {semantic_score}%. "
                f"Missing: {missing_str}. Verdict: {verdict}."
            )
        return result

    def generate_gap_summary(
        self,
        resume_context: str,
        jd_text: str,
        gaps: list[str],
        missing_keywords: list[str],
        skill_clusters: dict,
    ) -> str:
        """Generate a human-readable summary of WHY the resume doesn't fit."""
        gaps_str = "; ".join(gaps[:4]) if gaps else "none identified"
        missing_str = ", ".join(missing_keywords[:8]) or "none"

        # Build cluster gap info
        cluster_gaps = []
        for name, data in (skill_clusters or {}).items():
            cov = data.get("coverage", 0)
            if cov < 60:
                miss = ", ".join(data.get("missing_terms", [])[:3])
                cluster_gaps.append(f"{name} ({cov}% coverage, missing: {miss})")
        cluster_str = "; ".join(cluster_gaps[:3]) if cluster_gaps else "none"

        prompt = (
            f"Resume: {resume_context[:600]}\n\n"
            f"Job: {jd_text[:600]}\n\n"
            f"Gaps: {gaps_str}\n"
            f"Missing keywords: {missing_str}\n"
            f"Weak skill clusters: {cluster_str}\n\n"
            f"Write a 3-4 sentence summary explaining why this resume is not a strong fit "
            f"for this job. Be specific about what experience or skills are missing."
        )
        result = self._generate(prompt)
        if len(result) < 20:
            result = (
                f"Key gaps: {gaps_str}. "
                f"Missing keywords: {missing_str}. "
                f"Weak clusters: {cluster_str}."
            )
        return result

    def generate_tailoring_suggestions(
        self,
        resume_context: str,
        jd_text: str,
        missing_keywords: list[str],
        gaps: list[str],
        skill_clusters: dict,
        quantification_score: int,
    ) -> list[str]:
        """Generate actionable suggestions to tailor the resume for this JD."""
        suggestions = []

        # Rule-based suggestions (always reliable)
        if missing_keywords:
            top_missing = ", ".join(missing_keywords[:6])
            suggestions.append(
                f"Add these missing keywords to your Skills or Summary section: {top_missing}"
            )

        # Cluster-specific suggestions
        for name, data in (skill_clusters or {}).items():
            cov = data.get("coverage", 0)
            if cov < 50:
                miss = data.get("missing_terms", [])[:3]
                if miss:
                    suggestions.append(
                        f"Strengthen your {name} coverage — add experience with: {', '.join(miss)}"
                    )

        # Quantification
        if quantification_score < 8:
            suggestions.append(
                "Add more quantified achievements to your bullet points — "
                "use $, %, numbers (e.g., 'reduced costs by 30%', 'managed $2M budget')"
            )

        # Category gaps
        for gap in (gaps or []):
            if "placement" in gap.lower() or "summary" in gap.lower():
                suggestions.append(
                    "Move your most relevant skills to the top of your Summary section — "
                    "ATS systems weight keywords in Summary/Title 3x higher"
                )
                break

        # LLM-generated suggestion
        missing_str = ", ".join(missing_keywords[:5]) or "none"
        prompt = (
            f"Resume: {resume_context[:500]}\n"
            f"Job: {jd_text[:500]}\n"
            f"Missing: {missing_str}\n\n"
            f"Give 2 specific, actionable suggestions to tailor this resume for this job. "
            f"Be concrete — mention exact skills or phrases to add."
        )
        llm_result = self._generate(prompt)
        if len(llm_result) > 20:
            suggestions.append(llm_result)

        return suggestions[:6]  # cap at 6 suggestions
