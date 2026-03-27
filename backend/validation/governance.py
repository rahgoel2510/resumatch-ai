"""Validation Layer — Governance engine.

Configurable policy rules, approval gates, and threshold enforcement.
Policies are loaded from governance.json (or defaults) and evaluated
against every analysis result before it's returned to the user.

Governance covers:
  1. Quality gates — minimum score thresholds to trust a result
  2. Approval rules — conditions that flag results for human review
  3. Policy enforcement — hard rules that block or modify output
  4. Data governance — PII limits, retention rules
"""

import json
import os
from dataclasses import dataclass, field
from enum import Enum

from config import GOVERNANCE_CONFIG_FILE


class ApprovalStatus(str, Enum):
    APPROVED = "approved"           # passes all gates automatically
    FLAGGED = "flagged_for_review"  # needs human review
    BLOCKED = "blocked"             # hard policy violation


@dataclass
class GovernancePolicy:
    """Configurable governance thresholds and rules."""

    # Quality gates — minimum thresholds
    min_confidence_score: float = 0.25
    min_chunks_retrieved: int = 1
    min_ats_score_for_apply: int = 30
    max_missing_keyword_ratio: float = 0.85  # if >85% keywords missing, flag it

    # Approval gates — conditions that require human review
    flag_if_all_resumes_below: int = 30      # flag if ALL resumes score below this
    flag_if_pii_detected_in_output: bool = True
    flag_if_confidence_below: float = 0.3
    flag_if_guardrail_violations: int = 1    # flag if >= N violations

    # Hard policy rules
    block_if_no_resumes: bool = True
    block_if_input_too_short: int = 20       # min chars
    max_pii_in_output: int = 0               # 0 = zero tolerance
    max_response_latency_ms: float = 60000   # 60s timeout

    # Data governance
    max_resume_size_chars: int = 50000
    pii_redaction_required: bool = True
    audit_logging_required: bool = True
    feedback_collection_enabled: bool = True

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items()}


def load_governance_policy() -> GovernancePolicy:
    """Load governance policy from config file, or use defaults."""
    if os.path.exists(GOVERNANCE_CONFIG_FILE):
        try:
            with open(GOVERNANCE_CONFIG_FILE, "r") as f:
                data = json.load(f)
            policy = GovernancePolicy()
            for key, value in data.items():
                if hasattr(policy, key):
                    setattr(policy, key, value)
            print(f"[Governance] Loaded policy from {GOVERNANCE_CONFIG_FILE}")
            return policy
        except (json.JSONDecodeError, Exception) as e:
            print(f"[Governance] Error loading config: {e}, using defaults")

    return GovernancePolicy()


def save_governance_policy(policy: GovernancePolicy):
    """Save current governance policy to config file."""
    with open(GOVERNANCE_CONFIG_FILE, "w") as f:
        json.dump(policy.to_dict(), f, indent=2)


@dataclass
class GovernanceResult:
    """Result of governance evaluation on an analysis."""
    status: ApprovalStatus = ApprovalStatus.APPROVED
    flags: list[str] = field(default_factory=list)
    blocked_reason: str = ""
    policy_applied: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "status": self.status.value,
            "flags": self.flags,
            "blocked_reason": self.blocked_reason,
            "policies_applied": self.policy_applied,
        }


def evaluate_governance(
    policy: GovernancePolicy,
    resumes: list[dict],
    confidence_score: float,
    pii_in_output: int,
    guardrail_violations: list[str],
    latency_ms: float,
    chunks_retrieved: int,
) -> GovernanceResult:
    """
    Evaluate governance rules against an analysis result.
    Returns approval status + any flags or blocks.
    """
    result = GovernanceResult()

    # ── Hard blocks ──

    if policy.block_if_no_resumes and not resumes:
        result.status = ApprovalStatus.BLOCKED
        result.blocked_reason = "No resumes available for analysis"
        result.policy_applied.append("block_if_no_resumes")
        return result

    if pii_in_output > policy.max_pii_in_output:
        result.status = ApprovalStatus.BLOCKED
        result.blocked_reason = f"PII detected in output ({pii_in_output} items, max allowed: {policy.max_pii_in_output})"
        result.policy_applied.append("max_pii_in_output")
        return result

    if latency_ms > policy.max_response_latency_ms:
        result.status = ApprovalStatus.BLOCKED
        result.blocked_reason = f"Response exceeded timeout ({latency_ms:.0f}ms > {policy.max_response_latency_ms:.0f}ms)"
        result.policy_applied.append("max_response_latency_ms")
        return result

    # ── Flagging rules ──

    if resumes:
        best_score = max(r.get("combined_score", 0) for r in resumes)
        all_below = all(r.get("combined_score", 0) < policy.flag_if_all_resumes_below for r in resumes)

        if all_below:
            result.flags.append(f"All resumes scored below {policy.flag_if_all_resumes_below}%")
            result.policy_applied.append("flag_if_all_resumes_below")

    if confidence_score < policy.flag_if_confidence_below:
        result.flags.append(f"Low confidence: {confidence_score:.2f} (threshold: {policy.flag_if_confidence_below})")
        result.policy_applied.append("flag_if_confidence_below")

    if policy.flag_if_pii_detected_in_output and pii_in_output > 0:
        result.flags.append(f"PII detected in output: {pii_in_output} items (redacted)")
        result.policy_applied.append("flag_if_pii_detected_in_output")

    if len(guardrail_violations) >= policy.flag_if_guardrail_violations:
        result.flags.append(f"Guardrail violations: {', '.join(guardrail_violations)}")
        result.policy_applied.append("flag_if_guardrail_violations")

    if chunks_retrieved < policy.min_chunks_retrieved:
        result.flags.append(f"Insufficient retrieval: {chunks_retrieved} chunks (min: {policy.min_chunks_retrieved})")
        result.policy_applied.append("min_chunks_retrieved")

    # Set status
    if result.flags:
        result.status = ApprovalStatus.FLAGGED

    return result
