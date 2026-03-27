"""Presentation Layer — FastAPI route definitions."""

import time
from fastapi import APIRouter, UploadFile, File
from pydantic import BaseModel

from presentation.schemas import (
    JobRequest, AnalysisResponse, HealthResponse, UploadResponse, ErrorResponse,
)
from services.analysis_service import AnalysisService
from data.history_store import history_store
from observability.metrics import metrics_collector
from observability.feedback import feedback_store, FeedbackEntry
from observability.success_metrics import success_tracker
from validation.audit_logger import audit_logger
from validation.governance import save_governance_policy

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
# Core
# ------------------------------------------------------------------

@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_job(request: JobRequest):
    result = _svc().analyze_job(request.job_description)

    # Save to history
    best = result.get("resumes", [{}])[0] if result.get("resumes") else {}
    history_id = history_store.save(
        job_url=request.job_url,
        job_title=request.job_title,
        company=request.company,
        jd_snippet=request.job_description[:500],
        best_resume=result.get("best_resume", ""),
        best_score=best.get("combined_score", 0),
        best_verdict=best.get("verdict", ""),
        resume_count=len(result.get("resumes", [])),
        results=result.get("resumes", []),
    )
    result["history_id"] = history_id
    return result


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
# History
# ------------------------------------------------------------------

@router.get("/history")
async def list_history(limit: int = 50, offset: int = 0, q: str = ""):
    """List or search analysis history."""
    if q:
        entries = history_store.search(q, limit=limit)
    else:
        entries = history_store.list_recent(limit=limit, offset=offset)
    return {"entries": entries, "total": history_store.count()}


@router.get("/history/{entry_id}")
async def get_history_entry(entry_id: str):
    """Get a single history entry with full analysis results."""
    entry = history_store.get_by_id(entry_id)
    if not entry:
        return {"error": "Not found"}
    return entry


@router.delete("/history/{entry_id}")
async def delete_history_entry(entry_id: str):
    """Delete a history entry."""
    deleted = history_store.delete(entry_id)
    return {"deleted": deleted}


# ------------------------------------------------------------------
# Governance
# ------------------------------------------------------------------

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


@router.get("/governance/policy")
async def get_governance_policy():
    return _svc().governance_policy.to_dict()


@router.patch("/governance/policy")
async def update_governance_policy(req: PolicyUpdateRequest):
    policy = _svc().governance_policy
    for key, value in req.model_dump(exclude_none=True).items():
        if hasattr(policy, key):
            setattr(policy, key, value)
    save_governance_policy(policy)
    return {"message": "Policy updated", "policy": policy.to_dict()}


# ------------------------------------------------------------------
# Observability
# ------------------------------------------------------------------

@router.get("/metrics")
async def get_metrics():
    return metrics_collector.get_summary()


@router.get("/dashboard")
async def get_dashboard():
    return success_tracker.get_dashboard()


@router.get("/audit")
async def get_audit(n: int = 20):
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
    return feedback_store.get_accuracy_stats()
