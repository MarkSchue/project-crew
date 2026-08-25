"""Evaluation dataset and result models (masterplan section 20.3, plan
milestone M8.2).

Mirrors the dataset shape in masterplan section 20.3: input fixture,
expected structured properties, required/prohibited behaviors,
deterministic validators, model/prompt version, baseline, and regression
threshold.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


@dataclass(frozen=True)
class EvalCase:
    name: str
    input: dict
    golden_output: dict
    expected_properties: dict[str, Any] = field(default_factory=dict)
    required_behaviors: list[str] = field(default_factory=list)
    prohibited_behaviors: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvaluationDataset:
    schema_version: str
    capability_id: str
    model_version: str
    prompt_version: str
    baseline_pass_rate: float
    minimum_pass_rate: float
    cases: list[EvalCase]


@dataclass(frozen=True)
class CaseResult:
    name: str
    passed: bool
    failures: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class EvaluationResult:
    capability_id: str
    total_cases: int
    passed_cases: int
    minimum_pass_rate: float
    case_results: list[CaseResult] = field(default_factory=list)

    @property
    def pass_rate(self) -> float:
        if self.total_cases == 0:
            return 0.0
        return self.passed_cases / self.total_cases

    @property
    def meets_threshold(self) -> bool:
        return self.pass_rate >= self.minimum_pass_rate
