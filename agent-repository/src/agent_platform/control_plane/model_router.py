"""Model router and profiles (masterplan section 11.1, 26, 15.6, plan
milestone M5.3).

Resolves a SPOC's ``default_model_profile`` / ``routing.model_override``
against the model catalog, enforcing data-residency and classification
constraints as the most restrictive intersection (masterplan section
15.6). A violating combination is rejected at compile time (M3.2), not
at runtime.

Classification rule (per ``DEC-INCEPTION-001`` data-classification
matrix):

- ``public``/``internal``: any active profile.
- ``confidential``: profile must be flagged ``confidential_eligible``.
- ``restricted``: no model provider by default.
"""

from __future__ import annotations

from dataclasses import dataclass

from agent_platform.registries.model_registry import ModelRegistry
from agent_platform.registries.models import ModelCatalogEntry


class ModelResolutionError(ValueError):
    code = "MODEL_RESOLUTION"


@dataclass
class ModelRouter:
    model_registry: ModelRegistry

    def resolve(
        self,
        profile_id: str,
        *,
        classification: str,
        data_residency: str | None = None,
    ) -> ModelCatalogEntry:
        entry = self.model_registry.get(profile_id)
        if entry is None:
            raise ModelResolutionError(f"unknown model profile '{profile_id}'")
        if entry.status != "active":
            raise ModelResolutionError(f"model profile '{profile_id}' is '{entry.status}', not active")

        if classification == "restricted":
            raise ModelResolutionError(
                f"no model provider is eligible for classification 'restricted' by default"
            )
        if classification == "confidential" and not entry.confidential_eligible:
            raise ModelResolutionError(
                f"model profile '{profile_id}' is not confidential_eligible"
            )

        if data_residency and data_residency not in entry.data_residency:
            raise ModelResolutionError(
                f"model profile '{profile_id}' does not satisfy data_residency '{data_residency}' "
                f"(available: {entry.data_residency})"
            )

        return entry
