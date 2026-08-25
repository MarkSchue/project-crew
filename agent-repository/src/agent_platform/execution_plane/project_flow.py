"""Canonical `ProjectExecutionFlow` (masterplan section 13.1, plan
milestone M3.3, ADR-001, ADR-011, ADR-012).

Implements the step sequence from masterplan section 13.1 as small,
independently testable methods, called in sequence by ``run()``. Per plan
section 17.1's binding correction, this class depends only on
application ports (constructor-injected) and does not embed provisional
security, approval, persistence, or Git behavior directly — Phase 3 wires
it to in-memory/local test-double adapters; later phases swap in
production adapters without touching this class.

This is a plain-Python orchestrator, not a subclass of `crewai.Flow`
(documented deviation from ADR-001's long-term target — see
`docs/implementation/agent_platform/execution_plane/ProjectExecutionFlow.md`
for the rationale and the follow-up to swap in a real CrewAI Flow
subclass behind the same ports).
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from agent_platform.application.ports.approval_gateway import ApprovalGateway
from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.application.ports.policy_decision_point import PolicyDecisionPoint
from agent_platform.application.ports.run_state_store import RunStateStore
from agent_platform.application.ports.tool_executor import ToolExecutor
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.domain.run import (
    ApprovalRequest,
    DecisionRecord,
    ProjectRunState,
    RunError,
    RunManifest,
    RunStatus,
    ValidationResult,
)
from agent_platform.execution_plane.qa_gate import qa_validation_against_test_cases
from agent_platform.schemas.index_generator import rebuild_indexes
from agent_platform.telemetry.metrics import MetricsRegistry
from agent_platform.telemetry.run_summary import generate_run_summary_markdown

# Terminal/gate statuses at which the step loop stops early rather than
# continuing to the next step in the same call.
_EARLY_EXIT_STATUSES = {
    RunStatus.WAITING_FOR_HUMAN,
    RunStatus.BLOCKED,
    RunStatus.DEAD_LETTER,
    RunStatus.REJECTED,
    RunStatus.CANCELLED,
}

# Terminal statuses counted as a completed run for metrics.
_TERMINAL_STATUSES = {
    RunStatus.CLOSED,
    RunStatus.ACCEPTED,
    RunStatus.BLOCKED,
    RunStatus.REJECTED,
    RunStatus.CANCELLED,
    RunStatus.DEAD_LETTER,
}


@dataclass
class CancellationToken:
    _cancelled: bool = False

    def cancel(self) -> None:
        self._cancelled = True

    def is_cancelled(self) -> bool:
        return self._cancelled


@dataclass
class FlowRunOptions:
    originating_agent_id: str
    qa_agent_id: str
    test_cases: list[dict] = field(default_factory=list)
    human_plan_approved: bool = True
    human_acceptance_approved: bool = True
    project_public_dir: Path | None = None
    summary_output_path: Path | None = None
    max_qa_attempts: int = 2


class ProjectExecutionFlow:
    def __init__(
        self,
        *,
        run_state_store: RunStateStore,
        event_ledger: EventLedger,
        approval_gateway: ApprovalGateway,
        policy: PolicyDecisionPoint,
        tool_executor: ToolExecutor,
        clock: Clock,
        id_generator: IdGenerator,
        metrics: MetricsRegistry | None = None,
    ) -> None:
        self.run_state_store = run_state_store
        self.event_ledger = event_ledger
        self.approval_gateway = approval_gateway
        self.policy = policy
        self.tool_executor = tool_executor
        self.clock = clock
        self.id_generator = id_generator
        self.metrics = metrics

    # -- public API ---------------------------------------------------

    def start(self, manifest: RunManifest, options: FlowRunOptions, cancellation_token: CancellationToken | None = None) -> ProjectRunState:
        state = self.run_state_store.load(manifest.run_id, manifest.attempt_id)
        if state is None:
            state = ProjectRunState(manifest=manifest, status=RunStatus.LEASED)
            self._save(state)
        else:
            self._reset_if_cancelled(state)
        return self._run(state, options, cancellation_token)

    def resume(self, run_id: str, attempt_id: str, options: FlowRunOptions, cancellation_token: CancellationToken | None = None) -> ProjectRunState:
        state = self.run_state_store.load(run_id, attempt_id)
        if state is None:
            raise KeyError(f"no persisted state for run_id={run_id} attempt_id={attempt_id}")
        self._reset_if_cancelled(state)
        return self._run(state, options, cancellation_token)

    @staticmethod
    def _reset_if_cancelled(state: ProjectRunState) -> None:
        """A resumed run that was previously interrupted (cancelled before
        or during a step) restarts from its last completed step rather than
        remaining stuck in the terminal `cancelled` status."""
        if state.status == RunStatus.CANCELLED:
            state.status = RunStatus.RUNNING

    def start_new_attempt(self, previous_state: ProjectRunState) -> ProjectRunState:
        """Create a new attempt under the same run (QA rework, plan
        section 19.2 / ADR-014), resuming from `execute_bounded_crews`."""
        new_attempt_id = self.id_generator.new_id("attempt")
        new_manifest = previous_state.manifest.model_copy(update={"attempt_id": new_attempt_id})
        preserved_steps = [
            s
            for s in previous_state.completed_steps
            if s
            in (
                "load_run_manifest",
                "preflight_policy_check",
                "hydrate_typed_state",
                "create_execution_plan",
                "human_plan_approval_if_required",
            )
        ]
        new_state = ProjectRunState(
            manifest=new_manifest,
            status=RunStatus.RUNNING,
            resolved_agents=list(previous_state.resolved_agents),
            input_artifacts=list(previous_state.input_artifacts),
            qa_rework_count=previous_state.qa_rework_count,
            completed_steps=preserved_steps,
        )
        self._save(new_state)
        return new_state

    # -- step sequence --------------------------------------------------

    def _run(
        self, state: ProjectRunState, options: FlowRunOptions, cancellation_token: CancellationToken | None
    ) -> ProjectRunState:
        steps: list[tuple[str, Any]] = [
            ("load_run_manifest", self._step_load_run_manifest),
            ("preflight_policy_check", self._step_preflight_policy_check),
            ("hydrate_typed_state", self._step_hydrate_typed_state),
            ("create_execution_plan", self._step_create_execution_plan),
            (
                "human_plan_approval_if_required",
                lambda s: self._step_human_plan_approval_if_required(s, options),
            ),
            ("execute_bounded_crews", self._step_execute_bounded_crews),
            ("validate_outputs", self._step_validate_outputs),
            ("remediate_if_allowed", self._step_remediate_if_allowed),
            (
                "qa_validation_against_test_cases",
                lambda s: self._step_qa_validation(s, options),
            ),
            (
                "human_acceptance_if_required",
                lambda s: self._step_human_acceptance_if_required(s, options),
            ),
            ("stage_changes", self._step_stage_changes),
            ("create_commit_or_pull_request", self._step_create_commit_or_pull_request),
            (
                "finalize_run_summary",
                lambda s: self._step_finalize_run_summary(s, options),
            ),
            (
                "update_project_indexes",
                lambda s: self._step_update_project_indexes(s, options),
            ),
        ]

        started = time.monotonic()
        was_terminal = state.status in _TERMINAL_STATUSES

        for step_id, step_fn in steps:
            if cancellation_token and cancellation_token.is_cancelled():
                state.status = RunStatus.CANCELLED
                self._emit(state, "cancellation", "run_cancelled", {})
                self._save(state)
                self._record_terminal_metrics(state, started, was_terminal)
                return state

            if state.has_completed(step_id):
                continue

            step_fn(state)
            state.record_step_complete(step_id)
            self._save(state)

            if state.status in _EARLY_EXIT_STATUSES:
                break

        self._record_terminal_metrics(state, started, was_terminal)
        return state

    def _record_terminal_metrics(
        self, state: ProjectRunState, started: float, was_terminal: bool
    ) -> None:
        if self.metrics is None:
            return
        self.metrics.observe(
            "run_duration_seconds",
            time.monotonic() - started,
            labels={"workflow": state.manifest.workflow_id},
        )
        if state.status in _TERMINAL_STATUSES and not was_terminal:
            self.metrics.inc(
                "run_completion_total",
                labels={"status": state.status.value, "workflow": state.manifest.workflow_id},
            )
            if state.status is RunStatus.DEAD_LETTER:
                self.metrics.inc(
                    "run_dead_letter_total",
                    labels={"workflow": state.manifest.workflow_id},
                )

    def _step_load_run_manifest(self, state: ProjectRunState) -> None:
        self._emit(state, "load_run_manifest", "run_manifest_loaded", {"manifest_hash": state.manifest.manifest_hash})

    def _step_preflight_policy_check(self, state: ProjectRunState) -> None:
        decision = self.policy.evaluate(action="preflight_execute", context={"manifest": state.manifest.spoc_id})
        state.decisions.append(
            DecisionRecord(decision="preflight_policy", reason=decision.reason, actor_type="system", actor_id="policy_engine")
        )
        self._emit(
            state,
            "preflight_policy_check",
            "policy_decision_recorded",
            {"allowed": decision.allowed, "policy_decision_id": decision.policy_decision_id},
        )
        if not decision.allowed:
            state.status = RunStatus.BLOCKED
            state.errors.append(RunError(error_code="policy_denied", message=decision.reason, retryable=False))

    def _step_hydrate_typed_state(self, state: ProjectRunState) -> None:
        state.input_artifacts = list(state.manifest.input_artifacts)
        state.resolved_agents = list(state.manifest.resolved_agents)
        self._emit(state, "hydrate_typed_state", "state_hydrated", {"input_artifact_count": len(state.input_artifacts)})

    def _step_create_execution_plan(self, state: ProjectRunState) -> None:
        state.decisions.append(
            DecisionRecord(
                decision="execution_plan_created",
                reason=f"execution_mode={state.manifest.execution_mode}",
                actor_type="system",
                actor_id="control_plane",
            )
        )
        self._emit(state, "create_execution_plan", "execution_plan_created", {"execution_mode": state.manifest.execution_mode})

    def _step_human_plan_approval_if_required(self, state: ProjectRunState, options: FlowRunOptions) -> None:
        if not state.manifest.approval_required:
            self._emit(state, "human_plan_approval_if_required", "approval_skipped", {"reason": "not_required"})
            return

        approval_id = self.id_generator.new_id("approval")
        self.approval_gateway.request_approval(
            ApprovalRequest(approval_id=approval_id, scope="execution_plan", subject=state.manifest.spoc_id)
        )
        if options.human_plan_approved:
            self.approval_gateway.resolve(approval_id, approved=True)
            state.approval_requests.append(
                ApprovalRequest(approval_id=approval_id, scope="execution_plan", subject=state.manifest.spoc_id, status="approved")
            )
            self._emit(state, "human_plan_approval_if_required", "plan_approved", {"approval_id": approval_id})
        else:
            state.status = RunStatus.WAITING_FOR_HUMAN
            state.approval_requests.append(
                ApprovalRequest(approval_id=approval_id, scope="execution_plan", subject=state.manifest.spoc_id, status="pending")
            )
            self._emit(state, "human_plan_approval_if_required", "plan_approval_pending", {"approval_id": approval_id})

    def _step_execute_bounded_crews(self, state: ProjectRunState) -> None:
        # Phase 3 vertical slice: no real CrewAI/agent execution. The
        # declared output artifacts are treated as produced once a
        # resolved primary agent exists (masterplan section 27 vertical
        # slice proves the control model, not maximum intelligence).
        state.output_artifacts = list(state.manifest.output_artifacts)
        state.status = RunStatus.RUNNING
        self._emit(
            state,
            "execute_bounded_crews",
            "bounded_crew_executed",
            {"output_artifact_count": len(state.output_artifacts)},
        )

    def _step_validate_outputs(self, state: ProjectRunState) -> None:
        passed = len(state.output_artifacts) == len(state.manifest.output_artifacts) and bool(state.output_artifacts)
        state.validation_results.append(
            ValidationResult(validator="output_artifact_presence", passed=passed)
        )
        self._emit(state, "validate_outputs", "outputs_validated", {"passed": passed})

    def _step_remediate_if_allowed(self, state: ProjectRunState) -> None:
        self._emit(state, "remediate_if_allowed", "remediation_not_needed", {})

    def _step_qa_validation(self, state: ProjectRunState, options: FlowRunOptions) -> None:
        outcome = qa_validation_against_test_cases(
            run_id=state.manifest.run_id,
            attempt_id=state.manifest.attempt_id,
            originating_agent_id=options.originating_agent_id,
            qa_agent_id=options.qa_agent_id,
            test_cases=options.test_cases,
            tool_executor=self.tool_executor,
            event_ledger=self.event_ledger,
            clock=self.clock,
            id_generator=self.id_generator,
            qa_rework_count=state.qa_rework_count,
            max_attempts=options.max_qa_attempts,
        )
        state.qa_rework_count = outcome.qa_rework_count

        if outcome.next_state == "specialist_review":
            state.status = RunStatus.REVIEW
        elif outcome.next_state == "return_to_originating_agent":
            state.status = RunStatus.REJECTED
        else:  # dead_letter
            state.status = RunStatus.DEAD_LETTER
            self._emit(
                state,
                "qa_validation_against_test_cases",
                "human_escalation_required",
                {"failing_test_case_ids": outcome.failing_test_case_ids},
            )

    def _step_human_acceptance_if_required(self, state: ProjectRunState, options: FlowRunOptions) -> None:
        if not state.manifest.approval_required:
            self._emit(state, "human_acceptance_if_required", "acceptance_skipped", {"reason": "not_required"})
            return
        if options.human_acceptance_approved:
            state.status = RunStatus.ACCEPTED
            self._emit(state, "human_acceptance_if_required", "acceptance_granted", {})
        else:
            state.status = RunStatus.WAITING_FOR_HUMAN
            self._emit(state, "human_acceptance_if_required", "acceptance_pending", {})

    def _step_stage_changes(self, state: ProjectRunState) -> None:
        # GitWorkspace adapter is a Phase 4 concern (ADR-006); no-op here.
        self._emit(state, "stage_changes", "changes_staged_noop", {"reason": "git_workspace_not_configured"})

    def _step_create_commit_or_pull_request(self, state: ProjectRunState) -> None:
        self._emit(state, "create_commit_or_pull_request", "commit_noop", {"reason": "git_workspace_not_configured"})

    def _step_finalize_run_summary(self, state: ProjectRunState, options: FlowRunOptions) -> None:
        events = self.event_ledger.events_for_run(state.manifest.run_id)
        summary_markdown = generate_run_summary_markdown(state, events)
        if options.summary_output_path:
            options.summary_output_path.write_text(summary_markdown, encoding="utf-8")
        state.status = RunStatus.CLOSED if state.status == RunStatus.ACCEPTED else state.status
        self._emit(state, "finalize_run_summary", "run_summary_generated", {"event_count": len(events)})

    def _step_update_project_indexes(self, state: ProjectRunState, options: FlowRunOptions) -> None:
        if options.project_public_dir:
            rebuild_indexes(options.project_public_dir)
        self._emit(state, "update_project_indexes", "indexes_updated", {})

    # -- helpers ----------------------------------------------------------

    def _save(self, state: ProjectRunState) -> None:
        self.run_state_store.save(state.manifest.run_id, state.manifest.attempt_id, state)

    def _emit(self, state: ProjectRunState, step_id: str, event_type: str, payload: dict) -> None:
        self.event_ledger.append(
            RunEvent(
                event_id=self.id_generator.new_id("evt"),
                run_id=state.manifest.run_id,
                attempt_id=state.manifest.attempt_id,
                step_id=step_id,
                aggregate_id=state.manifest.run_id,
                event_type=event_type,
                timestamp=self.clock.now_iso(),
                actor=Actor(type="system", id="project_execution_flow"),
                payload=payload,
            )
        )
