# project-template-repository

Project-independent blueprints, governance rules, JSON Schemas, workflow
templates, and quality gates (masterplan section 7.2). A template release is
immutable; projects pin a template version and update through an explicit
migration.

## Layout

- `schemas/` — JSON Schemas for OKF, SPOC, agent, capability, project, and
  run-event front matter.
- `template_manifest.yaml` — semantic version and schema manifest for this
  template release.

Further template content (`project_skeleton/`, `templates/`, `workflows/`,
`governance/`) is added incrementally as later milestones need it (plan
milestones M1.1, M1.7).
