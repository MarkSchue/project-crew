"""Evaluation dataset loader (masterplan section 20.3, plan milestone
M8.2)."""

from __future__ import annotations

from pathlib import Path

import yaml

from agent_platform.evaluation.models import EvalCase, EvaluationDataset


def load_evaluation_dataset(path: Path) -> EvaluationDataset:
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    cases = [
        EvalCase(
            name=case["name"],
            input=case.get("input", {}),
            golden_output=case["golden_output"],
            expected_properties=case.get("expected_properties", {}),
            required_behaviors=case.get("required_behaviors", []),
            prohibited_behaviors=case.get("prohibited_behaviors", []),
        )
        for case in data["cases"]
    ]
    return EvaluationDataset(
        schema_version=data["schema_version"],
        capability_id=data["capability_id"],
        model_version=data["model_version"],
        prompt_version=data["prompt_version"],
        baseline_pass_rate=float(data["baseline_pass_rate"]),
        minimum_pass_rate=float(data["minimum_pass_rate"]),
        cases=cases,
    )


def iter_evaluation_datasets(root: Path):
    """Yield every `dataset.yaml` under `root` sorted by path."""
    for path in sorted(Path(root).glob("*/dataset.yaml")):
        yield path
