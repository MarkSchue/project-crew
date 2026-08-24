"""Package marker for agent_platform.application.ports.

Plan section 20.1 required ports:
RunStateStore, EventLedger, ArtifactRepository, GitWorkspace,
PolicyDecisionPoint, ApprovalGateway, ModelGateway, ToolExecutor,
AgentRuntime, WorkflowRegistry, IdentityContext, BudgetMeter, Clock,
IdGenerator, SecretsProvider, ObjectStore.

Phase 3 fully implements adapters (in `agent_platform.adapters`) for the
ports needed by the local vertical slice: RunStateStore, EventLedger,
ApprovalGateway, PolicyDecisionPoint, Clock, IdGenerator, ToolExecutor.
The remaining ports are defined here as thin Protocols so that
application/execution-plane code can depend on the full port set from day
one (plan section 20.2: "Flow classes call application services through
ports"), even though their concrete adapters are deferred to later phases.
"""
