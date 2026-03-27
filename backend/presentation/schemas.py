"""Presentation Layer — Pydantic request/response schemas."""

from pydantic import BaseModel


class JobRequest(BaseModel):
    job_description: str


class ResumeResult(BaseModel):
    filename: str
    ats_score: int
    keyword_score: int
    contextual_placement_score: int
    quantification_score: int
    quantification_examples: list[str]
    result_verbs_count: int
    cluster_score: int
    category_score: int
    skill_categories: dict
    skill_clusters: dict
    semantic_score: float
    combined_score: int
    missing_keywords_sample: list[str]
    matched_keywords_sample: list[str]
    strengths: list[str]
    gaps: list[str]
    verdict: str
    verdict_reasoning: str
    llm_analysis: str
    gap_summary: str = ""
    tailoring_suggestions: list[str] = []


class GovernanceInfo(BaseModel):
    status: str
    flags: list[str]
    blocked_reason: str
    policies_applied: list[str]


class AnalysisResponse(BaseModel):
    resumes: list[ResumeResult]
    best_resume: str | None
    recommendation: str
    governance: GovernanceInfo | None = None


class HealthResponse(BaseModel):
    status: str
    resumes_loaded: int


class UploadResponse(BaseModel):
    message: str


class ErrorResponse(BaseModel):
    error: str
