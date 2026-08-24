"""Requirement-to-delivery workflow (plan milestone M7.2, ADR-015).

The production, governed workflow that compiles a SPOC into an immutable
manifest and executes the canonical ``ProjectExecutionFlow`` (masterplan
section 10.2 ``requirement_to_delivery@1.2.0``). This class is the
``implementation.class`` referenced by the registry workflow entry, so
the registry (``agent-repository/registry/workflows/
requirement_to_delivery/1.2.0.yaml``) and this module agree.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.control_plane.spoc_compiler import CompileSpocService
from agent_platform.domain.run import ProjectRunState
from agent_platform.execution_plane.project_flow import FlowRunOptions, ProjectExecutionFlow


@dataclass
class RequirementToDeliveryFlow:
    compile_service: CompileSpocService
    flow: ProjectExecutionFlow

    def run(
        self,
        spoc: dict,
        *,
        project_id: str,
        options: FlowRunOptions,
    ) -> ProjectRunState:
        """Compile the SPOC and execute it end-to-end, including the QA
        rework loop (M3.8) and gate evidence generation."""
        manifest = self.compile_service.compile(spoc, project_id=project_id)
        return self.flow.start(manifest, options)
