"""Deterministic evaluation runner (masterplan section 20.3, plan
milestone M8.2).

Runs an evaluation dataset against an ``output`` produced for each case
(either the golden output or the result of a pluggable model adapter) and
checks:

- ``expected_properties`` — dot-paths into the output must equal the
  declared value;
- ``required_behaviors`` — every tag must be present in
  ``output["behaviors"]``;
- ``prohibited_behaviors`` — no tag may be present in
  ``output["behaviors"]``.

A capability below its declared ``minimum_pass_rate`` fails, which blocks
activation (the suite runs in CI on every registry change).
"""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from agent_platform.evaluation.models import CaseResult, EvaluationDataset, EvaluationResult

OutputAdapter = Callable[[str, dict], dict]


def _get_path(output: dict, path: str) -> Any:
    current: Any = output
    for part in path.split("."):
        if isinstance(current, dict):
            current = current.get(part)
        else:
            return None
    return current


def validate_case_output(case_output: dict, expected_properties: dict, required_behaviors: list[str], prohibited_behaviors: list[str]) -> list[str]:
    failures: list[str] = []
    for path, expected in expected_properties.items():
        actual = _get_path(case_output, path)
        if actual != expected:
            failures.append(f"expected_property {path}: expected {expected!r}, got {actual!r}")

    behaviors = set(case_output.get("behaviors") or [])
    for required in required_behaviors:
        if required not in behaviors:
            failures.append(f"missing required behavior '{required}'")
    for prohibited in prohibited_behaviors:
        if prohibited in behaviors:
            failures.append(f"present prohibited behavior '{prohibited}'")
    return failures


def run_evaluation(dataset: EvaluationDataset, adapter: OutputAdapter | None = None) -> EvaluationResult:
    """Run every case. If `adapter` is None, validate each case's golden
    output (the vertical-slice mode; real model adapters plug in here)."""
    case_results: list[CaseResult] = []
    for case in dataset.cases:
        output = adapter(dataset.capability_id, case.input) if adapter is not None else case.golden_output
        failures = validate_case_output(
            output,
            case.expected_properties,
            case.required_behaviors,
            case.prohibited_behaviors,
        )
        case_results.append(CaseResult(name=case.name, passed=not failures, failures=failures))

    passed = sum(1 for result in case_results if result.passed)
    return EvaluationResult(
        capability_id=dataset.capability_id,
        total_cases=len(dataset.cases),
        passed_cases=passed,
        minimum_pass_rate=dataset.minimum_pass_rate,
        case_results=case_results,
    )
