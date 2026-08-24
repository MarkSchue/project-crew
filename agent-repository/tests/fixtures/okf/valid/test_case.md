---
schema_version: "okf/1.1"
id: "TC-100"
type: "test_case"
title: "Verify OAuth2 login succeeds with valid credentials"
status: "active"
classification: "internal"
owner: "qa_agent"
created_at: "2026-08-24T08:00:00Z"
updated_at: "2026-08-24T08:00:00Z"
tags: ["auth", "test"]
source_refs: []
relations:
  - type: "validates"
    target: "US-100"
provenance:
  created_by_type: "human"
  created_by_id: "qa_lead"
  run_id: null
---

# TC-100: OAuth2 login with valid credentials

Given valid credentials, when the user logs in, then access is granted.
