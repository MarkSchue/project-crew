# Retention policy

**Owner role:** platform_engineering · **Introduced:** M8.4
**Aligned with:** `plan/decisions/inception_decisions.md` (retention rules),
ADR-018 (artifact storage).

## Retention classes

| Data class | Retention | Disposition |
|---|---|---|
| Accepted OKF artifacts | Indefinite | Project record (the system of record). Never deleted. |
| Git history | Indefinite | Retained; rewrites require the protected-branch process. |
| `events.jsonl` run evidence | Life of project + ≥1-year audit window | Archived to cold storage (not deleted) after the audit window. |
| Raw prompts / full model responses | Not copied into audit events by default | Debug traces retained 30 days, access-restricted. |
| Private agent workspaces (`private/<agent_id>/scratch`) | Life of run + 30 days | Purged unless referenced as evidence from an accepted artifact. |
| Backups | See backup/restore runbook | Rotated; at least one verified restorable copy at all times. |

## Rules

1. Deletion of an accepted OKF artifact is a governance-policy change and
   requires approval (`modify_governance_policy` is hard-denied to
   agents).
2. Archival preserves the append-only event stream; events are never
   mutated in place (ADR-013).
3. Retention is enforced by automated jobs, not by documentation alone
   (plan section 26, M8.7 is the enforcement follow-up; this document is
   the policy those jobs implement).
4. Every fixture and evaluation dataset declares its retention rule
   (plan section 25).

## Current status (vertical slice)

Retention *policy* is defined here; automated retention *enforcement* is
tracked as plan milestone M8.7 (privacy and retention enforcement) and is
not yet implemented.
