"""`mas agent scaffold <agent-id>` (masterplan section 11.3, plan M2.5).

Produces a schema-valid `status: draft` registry entry. Draft agents are
intentionally incomplete: `check_activation_readiness` (in
`agent_platform.registries.validators`) blocks the `draft -> active`
transition until a human fills in role/goal/capabilities/evaluations
(plan section 17.3 change map, M2.5 row).
"""

from __future__ import annotations

from pathlib import Path

import yaml

PLACEHOLDER_ROLE = "TODO: define this agent's role in one sentence."
PLACEHOLDER_GOAL = "TODO: define this agent's goal in one sentence."


def scaffold_agent_yaml(agent_id: str) -> dict:
    """Return a schema-valid, draft `agent.yaml` payload for `agent_id`."""
    return {
        "schema_version": "agent/1.1",
        "agent_id": agent_id,
        "version": "0.1.0",
        "name": agent_id.replace("_", " ").title(),
        "status": "draft",
        "role": PLACEHOLDER_ROLE,
        "goal": PLACEHOLDER_GOAL,
        "prompt_ref": f"registry/agents/{agent_id}/prompt.md",
        "capabilities": [],
        "allowed_tools": [],
        "allowed_classifications": ["internal"],
        "delegation": {"can_delegate": False, "allowed_capability_prefixes": [], "max_depth": 0},
        "human_escalation": {"mandatory_for": []},
        "health": {"evaluation_suite": None, "minimum_pass_rate": None},
    }


def scaffold_prompt_md(agent_id: str) -> str:
    return (
        f"# {agent_id} prompt\n\n"
        "TODO: write this agent's system prompt. Keep it aligned with the\n"
        "role and goal declared in `agent.yaml`.\n"
    )


def scaffold_eval_fixture(agent_id: str) -> dict:
    return {
        "schema_version": "eval-fixture/1.0",
        "agent_id": agent_id,
        "cases": [],
        "note": "TODO: add capability-specific evaluation cases before activation.",
    }


def scaffold_private_knowledge_index(agent_id: str) -> str:
    return f"# Private knowledge index for `{agent_id}`\n\n(No entries yet.)\n"


def scaffold_agent(registry_dir: Path, agent_id: str) -> Path:
    """Write the full scaffold for a new agent under
    `registry_dir/agents/<agent_id>/` and return that directory."""
    agent_dir = Path(registry_dir) / "agents" / agent_id
    (agent_dir / "tests").mkdir(parents=True, exist_ok=True)
    (agent_dir / "private_knowledge").mkdir(parents=True, exist_ok=True)

    (agent_dir / "agent.yaml").write_text(
        yaml.safe_dump(scaffold_agent_yaml(agent_id), sort_keys=False), encoding="utf-8"
    )
    (agent_dir / "prompt.md").write_text(scaffold_prompt_md(agent_id), encoding="utf-8")
    (agent_dir / "tests" / "evaluation_fixture.yaml").write_text(
        yaml.safe_dump(scaffold_eval_fixture(agent_id), sort_keys=False), encoding="utf-8"
    )
    (agent_dir / "private_knowledge" / "index.md").write_text(
        scaffold_private_knowledge_index(agent_id), encoding="utf-8"
    )
    return agent_dir
