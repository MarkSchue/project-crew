from pathlib import Path

import pytest

from agent_platform.control_plane.capability_inference import (
    FakeInferenceAdapter,
    InferredCandidate,
    process_inferred_candidates,
)
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def capability_registry(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    return load_capability_registry(fixtures_dir / "registry", schema_registry)


def test_fake_adapter_returns_configured_candidates():
    adapter = FakeInferenceAdapter(
        [InferredCandidate("architecture.trust_boundary_analysis", 0.8, "quoted text")]
    )
    candidates = adapter.propose("some procedure text")
    assert len(candidates) == 1
    assert candidates[0].capability_id == "architecture.trust_boundary_analysis"


def test_low_risk_candidate_is_auto_added(capability_registry):
    candidates = [InferredCandidate("documentation.api_reference", 0.9, "evidence")]
    outcome = process_inferred_candidates(
        candidates, capability_registry, explicit_capabilities=set(), allow_inference=True
    )
    assert outcome.auto_added == ["documentation.api_reference"]
    assert outcome.needs_human_review == []


def test_high_risk_candidate_needs_human_review(capability_registry):
    candidates = [InferredCandidate("security.secrets_management", 0.7, "evidence")]
    outcome = process_inferred_candidates(
        candidates, capability_registry, explicit_capabilities=set(), allow_inference=True
    )
    assert outcome.auto_added == []
    assert outcome.needs_human_review == ["security.secrets_management"]


def test_unknown_candidate_is_rejected(capability_registry):
    candidates = [InferredCandidate("totally.unknown", 0.5, "evidence")]
    outcome = process_inferred_candidates(
        candidates, capability_registry, explicit_capabilities=set(), allow_inference=True
    )
    assert outcome.rejected_unknown == ["totally.unknown"]


def test_already_explicit_candidate_is_ignored(capability_registry):
    candidates = [InferredCandidate("documentation.api_reference", 0.9, "evidence")]
    outcome = process_inferred_candidates(
        candidates,
        capability_registry,
        explicit_capabilities={"documentation.api_reference"},
        allow_inference=True,
    )
    assert outcome.auto_added == []
    assert outcome.needs_human_review == []
    assert outcome.rejected_unknown == []


def test_inference_disabled_returns_nothing(capability_registry):
    candidates = [InferredCandidate("documentation.api_reference", 0.9, "evidence")]
    outcome = process_inferred_candidates(
        candidates, capability_registry, explicit_capabilities=set(), allow_inference=False
    )
    assert outcome.auto_added == []
    assert outcome.needs_human_review == []
    assert outcome.rejected_unknown == []
