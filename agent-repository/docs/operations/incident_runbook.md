# Incident runbook

**Owner role:** platform_engineering · **Introduced:** M8.4
**Source of truth:** masterplan sections 16.4 (metrics) and 19 (error
handling and recovery).

## When to use this runbook

An alert fired (see `ops/alerts/platform_alerts.yml`) or an operator
observed an anomaly. The four seeded alerts are:

- `BudgetExhausted` (critical)
- `DeadLetterRateSpike`
- `PolicyDenialSpike`
- `ApprovalLeadTimeSLA`

## 1. Triage

1. Confirm the alert against the dashboard
   (`ops/dashboards/platform.json`) — is the metric sustained or a blip?
2. Identify the affected runs via `mas run status <run-id>` and the event
   ledger.

## 2. Incident classes and first actions

| Class | Evidence | First action |
|---|---|---|
| Budget exhausted | `budget_exhausted_total` + `budget_threshold_reached` events | Inspect the run manifest's `constraints`; confirm the limit is correct before raising it (a limit change is a governance change). |
| Dead-letter spike | `run_dead_letter_total`, dead-letter runs | Pull the run evidence (`mas run evidence <run-id>`); rework or escalate per the QA rework loop (masterplan section 13.5). |
| Policy-denial spike | `policy_denial_total` by `action` | Check for a misconfigured agent or a hard-deny action being attempted repeatedly; do **not** weaken policy to clear the alert. |
| Approval SLA breach | `approval_lead_time_seconds` p90 | Escalate to approvers; expired approvals block progress and cannot be auto-approved. |

## 3. Recovery playbooks

- **Resume a run:** `mas run resume <run-id>` — resumes from persisted
  state; inputs are re-hashed before resuming (masterplan section 19.3).
- **Restore from backup:** see
  [`backup_restore.md`](backup_restore.md); a restore rehearsal must have
  succeeded before relying on it in an incident.
- **Never silently continue** after a security or authorization error
  (masterplan section 19.3): investigate first.

## 4. Post-incident

1. Record the incident in the decision/RAID log (`public/decisions/`).
2. If a safety-relevant metric fired, review whether a policy, budget, or
   alert threshold needs a governed change (approval required).
3. Update this runbook if the recovery path was incomplete.
