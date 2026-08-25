"""Regression evaluation suite (masterplan section 20.3, plan milestone
M8.2 Definition of done).

For every capability claimed by an active registry agent, there must be a
versioned evaluation dataset under ``tests/evaluation/<capability>/``, and
the deterministic runner must meet the capability's declared
``minimum_pass_rate``. This suite runs in CI on every registry change and
blocks activation of a capability that fails its threshold.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from agent_platform.evaluation.loader import load_evaluation_dataset
from agent_platform.evaluation.runner import run_evaluation, validate_case_output
from agent_platform.registries.agent_registry import load_agent_registry
from agent_platform.registries.capability_registry import load_capability_registry
from agent_platform.schemas.okf_linter import SchemaRegistry

EVALUATION_DIR = Path(__file__).resolve().parent


def _active_agent_capabilities(schema_dir, fixtures_dir) -> set[str]:
    schema_registry = SchemaRegistry(schema_dir)
    registry_dir = fixtures_dir / "registry"
    capability_registry = load_capability_registry(registry_dir, schema_registry)
    agent_registry = load_agent_registry(registry_dir, schema_registry, capability_registry)
    claimed: set[str] = set()
    for agent in agent_registry:
        if agent.status == "active":
            for claim in agent.capabilities:
                claimed.add(claim.id)
    return claimed


def test_every_active_capability_has_an_evaluation_dataset(schema_dir, fixtures_dir):
    claimed = _active_agent_capabilities(schema_dir, fixtures_dir)
    assert claimed, "expected at least one claimed capability in the fixture registry"
    for capability_id in sorted(claimed):
        dataset_path = EVALUATION_DIR / capability_id / "dataset.yaml"
        assert dataset_path.exists(), f"missing evaluation dataset for capability '{capability_id}'"


def test_every_evaluation_dataset_meets_its_threshold(schema_dir, fixtures_dir):
    claimed = _active_agent_capabilities(schema_dir, fixtures_dir)
    for capability_id in sorted(claimed):
        dataset = load_evaluation_dataset(EVALUATION_DIR / capability_id / "dataset.yaml")
        result = run_evaluation(dataset)
        assert result.meets_threshold, (
            f"capability '{capability_id}' pass rate {result.pass_rate:.2f} "
            f"below minimum {result.minimum_pass_rate:.2f}"
        )


def test_validators_are_not_vacuous(schema_dir, fixtures_dir):
    """Removing a required behavior from a golden output must fail the
    case, proving the validators actually check the declared contract."""
    claimed = _active_agent_capabilities(schema_dir, fixtures_dir)
    for capability_id in sorted(claimed):
        dataset = load_evaluation_dataset(EVALUATION_DIR / capability_id / "dataset.yaml")
        for case in dataset.cases:
            if not case.required_behaviors:
                continue
            mutated = dict(case.golden_output)
            mutated["behaviors"] = [b for b in case.golden_output.get("behaviors", []) if b != case.required_behaviors[0]]
            failures = validate_case_output(
                mutated,
                case.expected_properties,
                case.required_behaviors,
                case.prohibited_behaviors,
            )
            assert failures, (
                f"capability '{capability_id}' case '{case.name}': removing required "
                f"behavior '{case.required_behaviors[0]}' was not detected"
            )
