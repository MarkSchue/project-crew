---
schema_version: "okf/1.1"
id: "US-400"
type: "user_story"
title: "User story with a mistyped tested_by relation"
status: "draft"
classification: "internal"
owner: "product_owner"
created_at: "2026-08-24T08:00:00Z"
updated_at: "2026-08-24T08:00:00Z"
tags: []
source_refs: []
relations:
  - type: "tested_by"
    target: "EPIC-400"
provenance:
  created_by_type: "human"
  created_by_id: "product_owner"
  run_id: null
---

# Invalid: `tested_by` points at an epic instead of a test_case (OKF-XREF-002).
