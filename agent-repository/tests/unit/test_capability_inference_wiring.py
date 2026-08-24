"""Governed capability inference wiring tests (plan milestone M5.5)."""

from pathlib import Path

import pytest

from agent_platform.adapters.approval import InMemoryApprovalGateway
from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.control_plane.capability_inference import FakeInferenceAdapter, InferredCandidate
from agent_platform.control_plane.policy_engine import PolicyEngine
from agent_platform.control_plane.spoc_compiler import CompileSpocService, SpocCompilationError
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def spoc_front_matter(fixtures_dir):
    return load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md").front_matter


def _build_compiler(schema_dir, fixtures_dir, *, candidates, auto_approve):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    ids = SequentialIdGenerator()
    return CompileSpocService(
        agent_registry=agent_registry,
        capability_registry=capability_registry,
        workflow_registry=workflow_registry,
        policy=PolicyEngine(id_generator=ids),
        clock=FixedClock(),
        id_generator=ids,
        inference_adapter=FakeInferenceAdapter(candidates),
        approval_gateway=InMemoryApprovalGateway(auto_approve=auto_approve),
    )


def test_low_risk_inferred_capability_is_auto_added_and_recorded(schema_dir, fixtures_dir, spoc_front_matter):
    compiler = _build_compiler(
        schema_dir,
        fixtures_dir,
        candidates=[InferredCandidate("architecture.requirement_traceability", 0.9, "quoted evidence")],
        auto_approve=False,
    )
    manifest = compiler.compile(spoc_front_matter, project_id="PRJ-001")
    # Recorded as inferred (not explicit) in the manifest.
    assert "architecture.requirement_traceability" in manifest.inferred_capabilities
    assert "architecture.requirement_traceability" in manifest.required_capabilities


def test_high_risk_inferred_capability_blocks_without_approval(schema_dir, fixtures_dir, spoc_front_matter):
    compiler = _build_compiler(
        schema_dir,
        fixtures_dir,
        candidates=[InferredCandidate("security.secrets_management", 0.7, "quoted evidence")],
        auto_approve=False,
    )
    with pytest.raises(SpocCompilationError) as exc_info:
        compiler.compile(spoc_front_matter, project_id="PRJ-001")
    assert "requires human approval" in str(exc_info.value)


def test_high_risk_inferred_capability_proceeds_with_approval(schema_dir, fixtures_dir, spoc_front_matter):
    compiler = _build_compiler(
        schema_dir,
        fixtures_dir,
        candidates=[InferredCandidate("security.secrets_management", 0.7, "quoted evidence")],
        auto_approve=True,
    )
    manifest = compiler.compile(spoc_front_matter, project_id="PRJ-001")
    assert "security.secrets_management" in manifest.inferred_capabilities
    assert "security.secrets_management" in manifest.required_capabilities


def test_explicit_capabilities_never_removed_by_inference(schema_dir, fixtures_dir, spoc_front_matter):
    compiler = _build_compiler(
        schema_dir,
        fixtures_dir,
        candidates=[InferredCandidate("security.oauth2.design", 0.9, "already explicit")],
        auto_approve=False,
    )
    manifest = compiler.compile(spoc_front_matter, project_id="PRJ-001")
    assert "security.oauth2.design" in manifest.required_capabilities
    assert "security.oauth2.design" not in manifest.inferred_capabilities
