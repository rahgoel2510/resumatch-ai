"""Business Logic Layer — orchestrates the refined 3-layer RAG pipeline.

Flow:
  REQUEST
    → Input guardrails (Validation)
    → Governance pre-check (Validation)
    → JD cleaning (Services)
    → Per-resume:
        → ATS scoring (ats_scorer)
        → Query sanitization + retrieval + access control (Retrieval)
        → LLM inference (Services)
        → Output guardrails (Validation)
        → Confidence scoring + fallback (Validation)
    → Governance evaluation (Validation)
    → Output sanitization (Validation)
    → Success KPI recording (Observability)
    → Audit logging (Validation)
  RESPONSE
"""

import time
import uuid

from data.model_repository import ModelRepository
from data.resume_repository import ResumeRepository
from knowledge.ingestion import ingest_document, IngestionResult
from retrieval.vector_store import VectorStore, NamespacedIndex
from retrieval.query_engine import QueryEngine
from services.jd_cleaner import clean_job_description
from services.llm_service import LLMService
from validation.guardrails import check_input, check_output
from validation.confidence import assess_confidence
from validation.output_sanitizer import sanitize_output
from validation.audit_logger import audit_logger, AuditEntry
from validation.governance import (
    load_governance_policy, evaluate_governance,
    GovernancePolicy, ApprovalStatus,
)
from observability.metrics import metrics_collector, RequestMetrics, Timer
from observability.success_metrics import success_tracker, AnalysisKPI
from ats_scorer import compute_ats_score
from config import TOP_K_RESULTS


class AnalysisService:
    """Orchestrates the full 3-layer RAG pipeline with governance."""

    def __init__(self, namespace: str = "default", owner: str = "default"):
        self._namespace = namespace
        self._owner = owner
        self._model_repo = ModelRepository()
        self._resume_repo = ResumeRepository()
        self._vector_store: VectorStore | None = None
        self._query_engine: QueryEngine | None = None
        self._llm_service: LLMService | None = None
        self._indexes: list[NamespacedIndex] = []
        self._ingestion_results: list[IngestionResult] = []
        self._governance: GovernancePolicy | None = None
        self._initialized = False

    # ------------------------------------------------------------------
    # Lifecycle
    # ------------------------------------------------------------------
    def initialize(self):
        if self._initialized:
            return

        self._governance = load_governance_policy()
        self._model_repo.load_all()
        self._vector_store = VectorStore(self._model_repo.embeddings)
        self._query_engine = QueryEngine(self._vector_store)
        self._llm_service = LLMService(self._model_repo)
        self._ingest_all_resumes()

        self._initialized = True
        print(f"[AnalysisService] Ready — {len(self._indexes)} resume(s), "
              f"namespace='{self._namespace}'")

    def _ingest_all_resumes(self):
        documents = self._resume_repo.list_all()
        self._indexes = []
        self._ingestion_results = []

        for doc in documents:
            # Governance: enforce max resume size
            if self._governance and len(doc.text) > self._governance.max_resume_size_chars:
                print(f"  [Governance] Skipped {doc.filename}: exceeds max size "
                      f"({len(doc.text)} > {self._governance.max_resume_size_chars})")
                continue

            ingestion = ingest_document(
                filename=doc.filename,
                raw_text=doc.text,
                namespace=self._namespace,
                owner=self._owner,
            )
            self._ingestion_results.append(ingestion)

            index = self._vector_store.create_index(
                filename=doc.filename,
                namespace=self._namespace,
                owner=self._owner,
                original_text=doc.text,
                clean_text=ingestion.clean_text,
                chunks=ingestion.chunks,
                pii_count=ingestion.pii_count,
            )
            self._indexes.append(index)

    def rebuild_indexes(self):
        self._ingest_all_resumes()

    @property
    def resume_count(self) -> int:
        return len(self._indexes)

    @property
    def governance_policy(self) -> GovernancePolicy:
        return self._governance

    def upload_resume(self, filename: str, file_obj) -> str:
        dest = self._resume_repo.save(filename, file_obj)
        self._ingest_all_resumes()
        return dest

    # ------------------------------------------------------------------
    # Main analysis pipeline
    # ------------------------------------------------------------------
    def analyze_job(self, job_description: str) -> dict:
        request_id = str(uuid.uuid4())[:8]
        start_time = time.time()
        pii_in_output = 0
        metrics = RequestMetrics(
            request_id=request_id,
            timestamp=start_time,
            resume_count=len(self._indexes),
        )

        # ── Governance: pre-check ──
        if not self._indexes and self._governance.block_if_no_resumes:
            return self._blocked_response("No resumes loaded. Add PDFs to resume_data/ and restart.")

        # ── Validation: input guardrails ──
        input_check = check_input(job_description)
        if not input_check.passed:
            return self._blocked_response(f"Input rejected: {'; '.join(input_check.violations)}")
        metrics.guardrail_violations.extend(f"input:{w}" for w in input_check.warnings)

        clean_jd = clean_job_description(input_check.modified_text)

        # ── Per-resume analysis ──
        results = []
        total_pii = 0
        for idx in self._indexes:
            result, resume_pii = self._analyze_single(idx, clean_jd, metrics)
            results.append(result)
            total_pii += idx.pii_redacted_count
            pii_in_output += resume_pii

        results.sort(key=lambda r: r["combined_score"], reverse=True)
        best = results[0] if results else None

        # ── Governance: evaluate result ──
        latency_ms = (time.time() - start_time) * 1000
        gov_result = evaluate_governance(
            policy=self._governance,
            resumes=results,
            confidence_score=metrics.confidence_score,
            pii_in_output=pii_in_output,
            guardrail_violations=metrics.guardrail_violations,
            latency_ms=latency_ms,
            chunks_retrieved=metrics.chunks_retrieved,
        )

        if gov_result.status == ApprovalStatus.BLOCKED:
            return self._blocked_response(gov_result.blocked_reason)

        # Build response
        response = {
            "resumes": results,
            "best_resume": best["filename"] if best else None,
            "recommendation": (
                f"Use '{best['filename']}' (score: {best['combined_score']}%). "
                f"{best['llm_analysis']}"
            ) if best else "No analysis available.",
            "governance": gov_result.to_dict(),
        }

        # ── Validation: output sanitization ──
        response = sanitize_output(response)

        # ── Observability: metrics + KPIs + audit ──
        metrics.latency_ms = latency_ms
        metrics.pii_detections = total_pii
        metrics_collector.record(metrics)

        success_tracker.record(AnalysisKPI(
            request_id=request_id,
            latency_ms=latency_ms,
            confidence=metrics.confidence_score,
            best_score=best["combined_score"] if best else 0,
            used_fallback=metrics.used_fallback,
            guardrail_violations=len(metrics.guardrail_violations),
            pii_redacted=total_pii,
            governance_status=gov_result.status.value,
            chunks_retrieved=metrics.chunks_retrieved,
            resume_count=len(self._indexes),
        ))

        audit_logger.log(AuditEntry(
            request_id=request_id,
            action="analyze",
            namespace=self._namespace,
            resumes_analyzed=len(self._indexes),
            pii_detections=total_pii,
            guardrail_violations=metrics.guardrail_violations,
            query_sanitized=metrics.query_sanitized,
            output_sanitized=metrics.output_sanitized,
            confidence_score=metrics.confidence_score,
            used_fallback=metrics.used_fallback,
            latency_ms=latency_ms,
            best_resume=best["filename"] if best else "",
            best_score=best["combined_score"] if best else 0,
        ))

        return response

    @staticmethod
    def _blocked_response(reason: str) -> dict:
        return {
            "resumes": [],
            "recommendation": reason,
            "best_resume": None,
            "governance": {
                "status": "blocked",
                "flags": [],
                "blocked_reason": reason,
                "policies_applied": [],
            },
        }

    def _analyze_single(self, index: NamespacedIndex, clean_jd: str, metrics: RequestMetrics) -> tuple[dict, int]:
        """Full pipeline for one resume. Returns (result_dict, pii_in_output_count)."""
        pii_in_output = 0

        # ATS scoring
        with Timer() as ats_timer:
            ats = compute_ats_score(index.text, clean_jd)
        metrics.ats_latency_ms += ats_timer.elapsed_ms

        # Retrieval
        with Timer() as ret_timer:
            query_result = self._query_engine.query(
                index=index,
                raw_query=clean_jd,
                k=TOP_K_RESULTS,
                namespace=self._namespace,
                owner=self._owner,
            )
        metrics.retrieval_latency_ms += ret_timer.elapsed_ms
        metrics.chunks_retrieved += query_result.chunk_count

        if query_result.sanitized_query.was_modified:
            metrics.query_sanitized = True

        sem_score = query_result.semantic_score
        combined = round(ats.overall_score * 0.70 + sem_score * 0.30)

        # LLM inference
        with Timer() as llm_timer:
            raw_llm = self._llm_service.analyze_resume_fit(
                resume_context=query_result.context,
                jd_text=clean_jd,
                ats_score=ats.overall_score,
                missing_keywords=ats.missing_keywords,
                verdict=ats.verdict,
                semantic_score=sem_score,
            )
        metrics.llm_latency_ms += llm_timer.elapsed_ms

        # Output guardrails
        output_check = check_output(raw_llm)
        if not output_check.passed:
            metrics.guardrail_violations.extend(f"output:{v}" for v in output_check.violations)
            metrics.output_sanitized = True
            pii_in_output += output_check.pii_found
        llm_text = output_check.modified_text

        # Confidence scoring + fallback
        confidence = assess_confidence(
            ats_score=ats.overall_score,
            semantic_score=sem_score,
            combined_score=combined,
            llm_output=llm_text,
            chunks_retrieved=query_result.chunk_count,
            missing_keywords=ats.missing_keywords,
            matched_keywords=ats.matched_keywords,
            verdict=ats.verdict,
            quantification_score=ats.quantification_score,
        )
        metrics.confidence_score = max(metrics.confidence_score, confidence.score)
        if confidence.used_fallback:
            metrics.used_fallback = True

        # Gap summary + tailoring suggestions
        gap_summary = ""
        tailoring_suggestions = []

        if ats.verdict in ("SKIP", "MAYBE — TAILOR FIRST") or combined < 55:
            gap_summary = self._llm_service.generate_gap_summary(
                resume_context=query_result.context,
                jd_text=clean_jd,
                gaps=ats.gaps,
                missing_keywords=ats.missing_keywords,
                skill_clusters=ats.skill_cluster_breakdown,
            )

        if "MAYBE" in ats.verdict or "TAILOR" in ats.verdict:
            tailoring_suggestions = self._llm_service.generate_tailoring_suggestions(
                resume_context=query_result.context,
                jd_text=clean_jd,
                missing_keywords=ats.missing_keywords,
                gaps=ats.gaps,
                skill_clusters=ats.skill_cluster_breakdown,
                quantification_score=ats.quantification_score,
            )

        return {
            "filename": index.filename,
            "ats_score": ats.overall_score,
            "keyword_score": ats.keyword_score,
            "contextual_placement_score": ats.contextual_placement_score,
            "quantification_score": ats.quantification_score,
            "quantification_examples": ats.quantification_examples,
            "result_verbs_count": ats.result_verbs_count,
            "cluster_score": ats.cluster_score,
            "category_score": ats.category_score,
            "skill_categories": ats.skill_category_breakdown,
            "skill_clusters": ats.skill_cluster_breakdown,
            "semantic_score": sem_score,
            "combined_score": combined,
            "missing_keywords_sample": ats.missing_keywords[:15],
            "matched_keywords_sample": ats.matched_keywords[:25],
            "strengths": ats.strengths,
            "gaps": ats.gaps,
            "verdict": ats.verdict,
            "verdict_reasoning": ats.verdict_reasoning,
            "llm_analysis": confidence.llm_output,
            "gap_summary": gap_summary,
            "tailoring_suggestions": tailoring_suggestions,
        }, pii_in_output
