---
schema_version: "spoc/1.1"
id: "SPOC-2026-0099"
type: "spoc"
title: "SPOC with an acceptance criterion missing test_case_refs"
status: "draft"
project_id: "PRJ-001"
owner: "security_workstream_lead"
created_at: "2026-08-22T08:00:00Z"
classification: "internal"
workflow: "requirement_to_delivery@1.2.0"

supplier:
  provided_by: "product_owner"
  inputs:
    - ref: "public/user_stories/US-002.md"
      required: true

procedure:
  objective: "Demonstrate the missing test_case_refs lint warning."
  execution_mode: "atomic"

output:
  artifacts:
    - target: "public/deliverables/example.md"
      schema: "okf/1.1"
      required: true
  acceptance_criteria:
    - id: "AC-1"
      statement: "Example criterion without linked test cases."
      validator: "example_validator"

consumer:
  next_role: "qa_agent"
  on_success: "request_human_approval"
  on_reject: "return_to_originating_agent"

retry_policy:
  max_attempts: 1
---

# SPOC-2026-0099

Missing `test_case_refs` on AC-1 should be a lint warning (OKF-COVERAGE-002),
not a hard schema failure.
