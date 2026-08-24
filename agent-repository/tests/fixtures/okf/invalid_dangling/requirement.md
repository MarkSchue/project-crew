---
schema_version: "okf/1.1"
id: "REQ-300"
type: "requirement"
title: "Requirement with a dangling relation"
status: "draft"
classification: "internal"
owner: "product_owner"
created_at: "2026-08-24T08:00:00Z"
updated_at: "2026-08-24T08:00:00Z"
tags: []
source_refs: []
relations:
  - type: "depends_on"
    target: "NOPE-999"
provenance:
  created_by_type: "human"
  created_by_id: "product_owner"
  run_id: null
---

# Invalid: `depends_on` targets an id that does not exist (OKF-XREF-001).
