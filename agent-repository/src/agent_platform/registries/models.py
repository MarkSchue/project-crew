"""Typed Pydantic models for registry entries (masterplan section 11, 12, 14).

These mirror the JSON Schemas in ``project-template-repository/schemas`` but
are the typed objects handed to application code (registry loaders expose
these, not raw dicts).
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class CapabilityEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    version: str
    description: str
    name: str | None = None
    parent: str | None = None
    aliases: list[str] = []
    requires: list[str] = []
    risk_level: str = "low"
    minimum_proficiency: int | None = None
    required_evaluations: list[str] = []
    status: str = "active"
    deprecated_by: str | None = None


class AgentCapabilityClaim(BaseModel):
    model_config = ConfigDict(extra="allow")

    id: str
    proficiency: int
    evidence_refs: list[str] = []


class AgentHealth(BaseModel):
    model_config = ConfigDict(extra="allow")

    evaluation_suite: str | None = None
    minimum_pass_rate: float | None = None


class AgentDefinition(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    agent_id: str
    version: str
    name: str
    status: str
    role: str
    goal: str
    prompt_ref: str | None = None
    default_model_profile: str | None = None
    capabilities: list[AgentCapabilityClaim]
    allowed_tools: list[str] = []
    allowed_classifications: list[str] = []
    delegation: dict = {}
    human_escalation: dict = {}
    health: AgentHealth = AgentHealth()


class SkillEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    skill_id: str
    version: str
    name: str
    description: str
    instructions_ref: str | None = None
    capabilities: list[str] = []
    status: str = "active"
    deprecated_by: str | None = None


class ToolEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    tool_id: str
    version: str
    description: str
    owner: str
    side_effect_category: str
    required_permissions: list[str] = []
    network_destinations: list[str] = []
    data_classifications: list[str] = []
    timeout_seconds: int | None = None
    retry_policy: dict = {}
    idempotent: bool = False
    audit_required: bool = True
    test_evidence_refs: list[str] = []
    security_evidence_refs: list[str] = []
    status: str = "active"
    deprecated_by: str | None = None


class ModelCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    schema_version: str
    profile_id: str
    provider: str
    model_id: str
    context_window_tokens: int | None = None
    supports_tool_use: bool = False
    supports_structured_output: bool = False
    cost_per_1k_input_tokens_usd: float | None = None
    cost_per_1k_output_tokens_usd: float | None = None
    data_residency: list[str] = []
    confidential_eligible: bool = False
    status: str = "active"
    deprecated_by: str | None = None


class WorkflowImplementation(BaseModel):
    model_config = ConfigDict(extra="allow", populate_by_name=True)

    module: str
    cls: str = Field(alias="class")


class WorkflowCatalogEntry(BaseModel):
    model_config = ConfigDict(extra="allow")

    workflow_id: str
    version: str
    implementation: WorkflowImplementation
    state_schema: str
    template_contract: str
    supported_execution_modes: list[str]
    compatible_platform: str
    status: str = "active"
    deprecated_by: str | None = None
