"""Capability inference (masterplan section 12.3).

An LLM may propose additional candidate capabilities from a SPOC's
procedure text. Candidates are structured, mapped to known capability IDs,
and gated by risk: low-risk candidates may be auto-added if policy
permits; high-risk or access-expanding candidates require human review.
Explicit capabilities are never removed.

Per masterplan execution principle 5, tests use a fake/stub inference
adapter; a real model-backed adapter is a Phase 5 model-routing concern
and is out of scope here. This module only defines the adapter protocol
and the deterministic post-processing around it.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from agent_platform.registries.capability_registry import CapabilityRegistry


@dataclass(frozen=True)
class InferredCandidate:
    """One LLM-proposed capability candidate."""

    capability_id: str
    confidence: float
    quoted_evidence: str


class InferenceAdapter(Protocol):
    """Pluggable adapter that proposes candidate capabilities from free
    text. Implementations may call a real model; tests use a fake."""

    def propose(self, procedure_text: str) -> list[InferredCandidate]: ...


class FakeInferenceAdapter:
    """Deterministic stand-in for tests: returns a fixed, pre-configured
    set of candidates regardless of input text."""

    def __init__(self, candidates: list[InferredCandidate] | None = None):
        self._candidates = candidates or []

    def propose(self, procedure_text: str) -> list[InferredCandidate]:
        return list(self._candidates)


@dataclass(frozen=True)
class InferenceOutcome:
    auto_added: list[str]
    needs_human_review: list[str]
    rejected_unknown: list[str]


def process_inferred_candidates(
    candidates: list[InferredCandidate],
    capability_registry: CapabilityRegistry,
    *,
    explicit_capabilities: set[str],
    allow_inference: bool,
    low_risk_auto_add: bool = True,
) -> InferenceOutcome:
    """Apply the compiler-side rules from masterplan section 12.3:

    - Map candidates to known capability IDs; reject unknown ones.
    - Add low-risk inferred capabilities automatically only if policy
      (``allow_inference`` and ``low_risk_auto_add``) permits.
    - Require human review for high-risk or access-expanding capabilities.
    - Never remove explicit capabilities (this function never touches
      ``explicit_capabilities``; it only classifies additional ones).
    """
    auto_added: list[str] = []
    needs_review: list[str] = []
    rejected_unknown: list[str] = []

    if not allow_inference:
        return InferenceOutcome(auto_added=[], needs_human_review=[], rejected_unknown=[])

    for candidate in candidates:
        canonical = capability_registry.resolve(candidate.capability_id)
        if canonical not in capability_registry:
            rejected_unknown.append(candidate.capability_id)
            continue
        if canonical in explicit_capabilities:
            continue  # already explicit; nothing to add

        entry = capability_registry.get(canonical)
        risk_level = entry.risk_level if entry else "high"

        if risk_level == "low" and low_risk_auto_add:
            auto_added.append(canonical)
        else:
            needs_review.append(canonical)

    return InferenceOutcome(
        auto_added=auto_added, needs_human_review=needs_review, rejected_unknown=rejected_unknown
    )
