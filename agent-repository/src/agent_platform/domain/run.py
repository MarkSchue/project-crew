"""Typed run state and manifest domain models (masterplan section 13.2,
plan milestone M3.1).

Pydantic models only; no CrewAI/FastAPI/SQLAlchemy/Git/cloud-SDK/model-
provider imports (plan section 20.2). State (de)serializes losslessly
to/from JSON for persistence and resume (plan M3.6).

Per masterplan section 13.2's note: full confidential document bodies are
never placed directly in state, only references (``ArtifactRef``).
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, ConfigDict


class RunStatus(str, Enum):
    """Mirrors the SPOC state machine (masterplan section 10.3) at the
    run/attempt level."""

    DRAFT = "draft"
    VALIDATED = "validated"
    READY = "ready"
    LEASED = "leased"
    RUNNING = "running"
    WAITING_FOR_HUMAN = "waiting_for_human"
    REVIEW = "review"
    ACCEPTED = "accepted"
    CLOSED = "closed"
    RETRY_PENDING = "retry_pending"
    BLOCKED = "blocked"
    REJECTED = "rejected"
    CANCELLED = "cancelled"
    DEAD_LETTER = "dead_letter"


class ArtifactRef(BaseModel):
    model_config = ConfigDict(extra="allow")

    ref: str
    content_hash: str | None = None
    classification: str = "internal"


class ResolvedAgent(BaseModel):
    model_config = ConfigDict(extra="allow")

    agent_id: str
    agent_version: str
    role: str = "primary"  # "primary" | "delegate"
    score: float | None = None


class CapabilityCandidate(BaseModel):
    model_config = ConfigDict(extra="allow")

    capability_id: str
    source: str  # "explicit" | "inferred"
    confidence: float | None = None
    approved: bool = True


class DecisionRecord(BaseModel):
    model_config = ConfigDict(extra="allow")

    decision: str
    reason: str
    actor_type: str  # "human" | "agent" | "system"
    actor_id: str


class ValidationResult(BaseModel):
    model_config = ConfigDict(extra="allow")

    validator: str
    passed: bool
    details: str = ""


class ApprovalRequest(BaseModel):
    model_config = ConfigDict(extra="allow")

    approval_id: str
    scope: str
    subject: str
    status: str = "pending"  # "pending" | "approved" | "rejected" | "expired"
    reason: str | None = None
    requested_at: str | None = None
    expires_at: str | None = None


class CostState(BaseModel):
    model_config = ConfigDict(extra="allow")

    spent_usd: float = 0.0
    max_total_cost_usd: float | None = None

    def remaining(self) -> float | None:
        if self.max_total_cost_usd is None:
            return None
        return max(0.0, self.max_total_cost_usd - self.spent_usd)

    def would_exceed(self, additional_cost_usd: float) -> bool:
        if self.max_total_cost_usd is None:
            return False
        return (self.spent_usd + additional_cost_usd) > self.max_total_cost_usd


class RunError(BaseModel):
    model_config = ConfigDict(extra="allow")

    error_code: str
    message: str
    retryable: bool = False


class RunManifest(BaseModel):
    """Immutable, compiled output of the SPOC compiler (masterplan section
    10.4). Nothing executes from a mutable SPOC file directly."""

    model_config = ConfigDict(extra="allow", frozen=True)

    schema_version: str = "run-manifest/1.0"
    project_id: str
    spoc_id: str
    spoc_version: str
    execution_key: str
    run_id: str
    attempt_id: str
    correlation_id: str
    workflow_id: str
    workflow_version: str
    execution_mode: str = "atomic"
    required_capabilities: list[str] = []
    inferred_capabilities: list[str] = []
    resolved_agents: list[ResolvedAgent] = []
    input_artifacts: list[ArtifactRef] = []
    output_artifacts: list[ArtifactRef] = []
    file_allowlist: list[str] = []
    max_runtime_seconds: int | None = None
    max_delegation_depth: int | None = None
    max_child_agent_calls: int | None = None
    max_total_cost_usd: float | None = None
    policy_bundle_version: str | None = None
    approval_required: bool = False
    manifest_hash: str | None = None


class ProjectRunState(BaseModel):
    """Typed Flow state (masterplan section 13.2, plan M3.1)."""

    model_config = ConfigDict(extra="allow")

    manifest: RunManifest
    status: RunStatus = RunStatus.LEASED
    capability_candidates: list[CapabilityCandidate] = []
    resolved_agents: list[ResolvedAgent] = []
    input_artifacts: list[ArtifactRef] = []
    output_artifacts: list[ArtifactRef] = []
    decisions: list[DecisionRecord] = []
    validation_results: list[ValidationResult] = []
    approval_requests: list[ApprovalRequest] = []
    cost: CostState = CostState()
    errors: list[RunError] = []
    qa_rework_count: int = 0
    technical_retry_count: int = 0
    completed_steps: list[str] = []

    def record_step_complete(self, step_id: str) -> None:
        if step_id not in self.completed_steps:
            self.completed_steps.append(step_id)

    def has_completed(self, step_id: str) -> bool:
        return step_id in self.completed_steps
