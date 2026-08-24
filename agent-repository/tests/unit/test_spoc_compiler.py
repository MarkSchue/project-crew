from pathlib import Path

import pytest

from agent_platform.adapters.clock_and_ids import FixedClock, SequentialIdGenerator
from agent_platform.adapters.policy import LocalDevPolicyDecisionPoint
from agent_platform.control_plane.spoc_compiler import CompileSpocService, SpocCompilationError
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.registries.workflow_registry import load_workflow_registry
from agent_platform.schemas.canonicalize import load_okf_file
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def compiler(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    workflow_registry = load_workflow_registry(registry_dir, schema_registry)

    def _make():
        id_generator = SequentialIdGenerator()
        policy = LocalDevPolicyDecisionPoint(decision_id_generator=id_generator)
        return CompileSpocService(
            agent_registry=agent_registry,
            capability_registry=capability_registry,
            workflow_registry=workflow_registry,
            policy=policy,
            clock=FixedClock(),
            id_generator=id_generator,
        )

    return _make


@pytest.fixture
def spoc_front_matter(fixtures_dir):
    doc = load_okf_file(fixtures_dir / "spoc" / "valid_spoc.md")
    return doc.front_matter


def test_compile_produces_manifest_with_split_agents(compiler, spoc_front_matter):
    service = compiler()
    manifest = service.compile(spoc_front_matter, project_id="PRJ-001")

    assert manifest.spoc_id == "SPOC-2026-0042"
    assert manifest.execution_mode == "delegated"
    assert manifest.approval_required is True  # classification: confidential
    assert manifest.manifest_hash is not None

    agent_ids = {a.agent_id: a.role for a in manifest.resolved_agents}
    assert agent_ids.get("security_architect") == "primary"
    assert agent_ids.get("architecture_writer") == "delegate"

    assert "architecture.requirement_traceability" in manifest.required_capabilities


def test_compile_is_deterministic_given_matching_id_sequence(compiler, spoc_front_matter):
    manifest_a = compiler().compile(spoc_front_matter, project_id="PRJ-001")
    manifest_b = compiler().compile(spoc_front_matter, project_id="PRJ-001")

    assert manifest_a.run_id == manifest_b.run_id
    assert manifest_a.execution_key == manifest_b.execution_key
    assert manifest_a.manifest_hash == manifest_b.manifest_hash


def test_compile_rejects_unknown_workflow(compiler, spoc_front_matter):
    spoc_front_matter = dict(spoc_front_matter)
    spoc_front_matter["workflow"] = "unknown_workflow@9.9.9"
    with pytest.raises(SpocCompilationError):
        compiler().compile(spoc_front_matter, project_id="PRJ-001")


def test_compile_rejects_unsupported_execution_mode(compiler, spoc_front_matter):
    spoc_front_matter = dict(spoc_front_matter)
    spoc_front_matter["procedure"] = dict(spoc_front_matter["procedure"])
    spoc_front_matter["procedure"]["execution_mode"] = "not_a_real_mode"
    with pytest.raises(SpocCompilationError):
        compiler().compile(spoc_front_matter, project_id="PRJ-001")
