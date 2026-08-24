"""Model router tests (plan milestone M5.3 Definition of done)."""

import pytest

from agent_platform.control_plane.model_router import ModelResolutionError, ModelRouter
from agent_platform.registries.model_registry import load_model_registry
from agent_platform.schemas.okf_linter import SchemaRegistry


@pytest.fixture
def router(schema_dir, fixtures_dir):
    schema_registry = SchemaRegistry(schema_dir)
    model_registry = load_model_registry(fixtures_dir / "registry", schema_registry)
    return ModelRouter(model_registry)


def test_resolve_internal_classification_succeeds(router):
    entry = router.resolve("reasoning_medium", classification="internal")
    assert entry.profile_id == "reasoning_medium"


def test_unknown_profile_rejected(router):
    with pytest.raises(ModelResolutionError):
        router.resolve("nonexistent", classification="internal")


def test_confidential_requires_confidential_eligible_profile(router):
    # reasoning_medium is NOT confidential_eligible.
    with pytest.raises(ModelResolutionError):
        router.resolve("reasoning_medium", classification="confidential")
    # reasoning_high IS confidential_eligible.
    assert router.resolve("reasoning_high", classification="confidential").confidential_eligible is True


def test_restricted_never_eligible(router):
    with pytest.raises(ModelResolutionError):
        router.resolve("reasoning_high", classification="restricted")


def test_data_residency_enforced(router):
    with pytest.raises(ModelResolutionError):
        router.resolve("reasoning_high", classification="internal", data_residency="ap-east-1")
    assert router.resolve("reasoning_high", classification="internal", data_residency="eu").data_residency == ["eu", "us"]
