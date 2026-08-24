"""SPOC compiler / run-manifest builder (masterplan section 10.4, plan
milestone M3.2, ADR-014 for identity, ADR-015 for workflow resolution).

Compiles a validated SPOC front-matter dict into an immutable
``RunManifest``. No execution starts from a mutable SPOC file directly;
it starts from this compiled manifest (masterplan section 10.4).

Reduced fidelity for the Phase 3 vertical slice, explicitly noted:

- Input hashing uses ``expected_hash`` if the SPOC declares one, otherwise
  a hash of the reference string itself (real content hashing requires
  the ``ArtifactRepository`` port, a Phase 4 concern per ADR-018).
- Schema/policy structural validation is assumed already done by
  ``mas project validate`` before compilation; this compiler only runs
  the compile-time policy check (approval requirements), not OKF schema
  validation.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.application.ports.policy_decision_point import PolicyDecisionPoint
from agent_platform.control_plane.capability_matcher import MatchRequest, match
from agent_platform.domain.ids import compute_execution_key
from agent_platform.domain.run import ArtifactRef, ResolvedAgent, RunManifest
from agent_platform.registries.agent_registry import AgentRegistry
from agent_platform.registries.capability_registry import CapabilityRegistry
from agent_platform.registries.workflow_registry import WorkflowRegistry
from agent_platform.schemas.canonicalize import compute_content_hash


class SpocCompilationError(ValueError):
    """Raised when a SPOC cannot be compiled into a manifest: unknown
    capability, missing workflow version, policy denial, or unresolved
    required capability coverage."""


@dataclass
class CompileSpocService:
    agent_registry: AgentRegistry
    capability_registry: CapabilityRegistry
    workflow_registry: WorkflowRegistry
    policy: PolicyDecisionPoint
    clock: Clock
    id_generator: IdGenerator

    def compile(self, spoc: dict, *, project_id: str) -> RunManifest:
        spoc_id = spoc["id"]
        spoc_version = spoc.get("content_hash") or compute_content_hash(spoc, "")
        classification = spoc.get("classification", "internal")

        workflow_id, workflow_version = _parse_workflow_ref(spoc["workflow"])
        workflow_entry = self.workflow_registry.get(workflow_id, workflow_version)
        if workflow_entry is None:
            raise SpocCompilationError(
                f"unknown workflow '{workflow_id}@{workflow_version}'"
            )

        procedure = spoc.get("procedure", {})
        execution_mode = procedure.get("execution_mode", "atomic")
        if execution_mode not in workflow_entry.supported_execution_modes:
            raise SpocCompilationError(
                f"workflow '{workflow_id}@{workflow_version}' does not support "
                f"execution_mode '{execution_mode}'"
            )

        explicit_capabilities = procedure.get("explicit_capabilities", [])
        match_request = MatchRequest(
            explicit_capabilities=explicit_capabilities,
            classification=classification,
        )
        match_result = match(match_request, self.agent_registry, self.capability_registry)
        if match_result.unresolved_capabilities:
            raise SpocCompilationError(
                f"no agent coverage for capabilities: {sorted(match_result.unresolved_capabilities)}"
            )

        resolved_agents: list[ResolvedAgent] = []
        if match_result.primary:
            primary_agent = self.agent_registry[match_result.primary.agent_id]
            resolved_agents.append(
                ResolvedAgent(
                    agent_id=primary_agent.agent_id,
                    agent_version=primary_agent.version,
                    role="primary",
                    score=match_result.primary.score,
                )
            )
        for delegate in match_result.delegate_candidates:
            delegate_agent = self.agent_registry[delegate.agent_id]
            resolved_agents.append(
                ResolvedAgent(
                    agent_id=delegate_agent.agent_id,
                    agent_version=delegate_agent.version,
                    role="delegate",
                    score=delegate.score,
                )
            )

        input_artifacts = [
            ArtifactRef(
                ref=item["ref"],
                content_hash=item.get("expected_hash") or _hash_ref(item["ref"]),
                classification=classification,
            )
            for item in spoc.get("supplier", {}).get("inputs", [])
        ]
        output_artifacts = [
            ArtifactRef(ref=item["target"], classification=classification)
            for item in spoc.get("output", {}).get("artifacts", [])
        ]

        file_allowlist = sorted(
            {a.ref for a in input_artifacts} | {a.ref for a in output_artifacts}
        )

        constraints = procedure.get("constraints", {})

        approval_required = self._requires_approval(spoc, classification)

        resolved_input_hashes = [a.content_hash for a in input_artifacts if a.content_hash]
        execution_key = compute_execution_key(
            project_id=project_id,
            spoc_id=spoc_id,
            spoc_version=spoc_version,
            resolved_input_hashes=resolved_input_hashes,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            policy_bundle_version="local-dev-policy/0.1.0",
        )

        run_id = self.id_generator.new_id("run")
        attempt_id = self.id_generator.new_id("attempt")
        correlation_id = self.id_generator.new_id("corr")

        manifest = RunManifest(
            project_id=project_id,
            spoc_id=spoc_id,
            spoc_version=spoc_version,
            execution_key=execution_key,
            run_id=run_id,
            attempt_id=attempt_id,
            correlation_id=correlation_id,
            workflow_id=workflow_id,
            workflow_version=workflow_version,
            execution_mode=execution_mode,
            required_capabilities=sorted(match_result.required_capabilities),
            resolved_agents=resolved_agents,
            input_artifacts=input_artifacts,
            output_artifacts=output_artifacts,
            file_allowlist=file_allowlist,
            max_runtime_seconds=constraints.get("max_runtime_seconds"),
            max_total_cost_usd=constraints.get("max_total_cost_usd"),
            approval_required=approval_required,
        )

        manifest_hash = compute_content_hash(manifest.model_dump(exclude={"manifest_hash"}), "")
        return manifest.model_copy(update={"manifest_hash": manifest_hash})

    def _requires_approval(self, spoc: dict, classification: str) -> bool:
        if classification in ("confidential", "restricted"):
            return True
        procedure = spoc.get("procedure", {})
        if procedure.get("prohibited_actions"):
            return True
        decision = self.policy.evaluate(
            action="compile_spoc",
            context={"classification": classification},
        )
        return not decision.allowed


def _parse_workflow_ref(workflow_ref: str) -> tuple[str, str]:
    workflow_id, _, version = workflow_ref.partition("@")
    if not version:
        raise SpocCompilationError(f"workflow ref '{workflow_ref}' must be '<id>@<version>'")
    return workflow_id, version


def _hash_ref(ref: str) -> str:
    return compute_content_hash({"ref": ref}, "")
