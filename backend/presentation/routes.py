"""Presentation Layer — FastAPI route definitions.

Thin layer: validates input, delegates to service, formats response.
"""

import time
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from presentation.schemas import (
    JobRequest, AnalysisResponse, HealthResponse, UploadResponse, ErrorResponse,
)
from services.analysis_service import AnalysisService
from observability.metrics import metrics_collector
from observability.feedback import feedback_store, FeedbackEntry
from observability.success_metrics import success_tracker
from validation.audit_logger import audit_logger
from validation.governance import save_governance_policy, GovernancePolicy

router = APIRouter()

_service: AnalysisService | None = None


def set_service(service: AnalysisService):
    global _service
    _service = service


def _svc() -> AnalysisService:
    if _service is None:
        raise RuntimeError("Service not initialized")
    return _service


# ------------------------------------------------------------------
# Core endpoints
# ------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_job(request: JobRequest):
    """Analyze a JD against all resumes with full governance pipeline."""
    return _svc().analyze_job(request.job_description)


@router.post("/upload-resume", response_model=UploadResponse | ErrorResponse)
async def upload_resume(file: UploadFile = File(...)):
    try:
        _svc().upload_resume(file.filename, file.file)
        return UploadResponse(message=f"Uploaded {file.filename} and rebuilt indexes.")
    except ValueError as e:
        return ErrorResponse(error=str(e))


@router.get("/health", response_model=HealthResponse)
async def health():
    return HealthResponse(status="ok", resumes_loaded=_svc().resume_count)


# ------------------------------------------------------------------
# Governance endpoints
# ------------------------------------------------------------------

@router.get("/governance/policy")
async def get_governance_policy():
    """Get current governance policy configuration."""
    return _svc().governance_policy.to_dict()


class PolicyUpdateRequest(BaseModel):
    min_confidence_score: float | None = None
    min_chunks_retrieved: int | None = None
    min_ats_score_for_apply: int | None = None
    flag_if_all_resumes_below: int | None = None
    flag_if_confidence_below: float | None = None
    flag_if_guardrail_violations: int | None = None
    max_pii_in_output: int | None = None
    max_response_latency_ms: float | None = None
    max_resume_size_chars: int | None = None


@router.patch("/governance/policy")
async def update_governance_policy(req: PolicyUpdateRequest):
    """Update governance policy thresholds."""
    policy = _svc().governance_policy
    updates = req.model_dump(exclude_none=True)
    for key, value in updates.items():
        if hasattr(policy, key):
            setattr(policy, key, value)
    save_governance_policy(policy)
    return {"message": "Policy updated", "policy": policy.to_dict()}


# ------------------------------------------------------------------
# Observability endpoints
# ------------------------------------------------------------------

@router.get("/metrics")
async def get_metrics():
    """Pipeline performance metrics."""
    return metrics_collector.get_summary()


@router.get("/dashboard")
async def get_dashboard():
    """Full KPI dashboard — latency, quality, governance, safety."""
    return success_tracker.get_dashboard()


@router.get("/audit")
async def get_audit(n: int = 20):
    """Recent audit log entries."""
    return {"entries": audit_logger.get_recent(n)}


class FeedbackRequest(BaseModel):
    resume_filename: str
    verdict: str
    combined_score: int
    user_action: str
    user_comment: str = ""
    jd_snippet: str = ""


@router.post("/feedback")
async def submit_feedback(req: FeedbackRequest):
    """Submit user feedback for continuous improvement."""
    feedback_store.record(FeedbackEntry(
        timestamp=time.time(),
        resume_filename=req.resume_filename,
        verdict=req.verdict,
        combined_score=req.combined_score,
        user_action=req.user_action,
        user_comment=req.user_comment,
        jd_snippet=req.jd_snippet[:200],
    ))
    return {"message": "Feedback recorded"}


@router.get("/feedback/stats")
async def feedback_stats():
    """Feedback accuracy statistics."""
    return feedback_store.get_accuracy_stats()
