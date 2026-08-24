# Definition of done (platform level)

Plan milestone M0.5. This is the **platform-level** Definition of Done —
the conditions a platform deliverable (a milestone, a module, a CLI
command) must satisfy. It is distinct from the **per-SPOC** Definition of
Done in masterplan section 23, which applies to a single executed work
package.

## Platform DoD checklist

A platform change is done only when **all** of the following hold:

1. **Schemas before prompts.** Any new artifact type has its JSON Schema
   (and OKF profile where applicable) committed and validated before any
   LLM-facing prompt consumes it (masterplan section 28.2).
2. **Contract tests.** Every port, tool, or registry entry has at least
   one passing contract/unit test; a changed public contract is reflected
   in its test in the same change.
3. **Documentation.** Every required code unit has an up-to-date
   `module.md`/class document (plan section 17.6) in the same change.
4. **Evidence.** Registry entries claiming a capability carry
   `evidence_refs`; new agents are `status: draft` and cannot be activated
   without passing `check_activation_readiness`.
5. **Determinism.** Matching, hashing, and index generation are
   deterministic (reproducible across repeated runs) and covered by a test.
6. **Fail-closed.** Policy decisions and validation failures fail closed;
   a test asserts the deny/error path.
7. **No secrets.** No commit introduces a secret; `content_hash`/audit
   fields are never hand-asserted.
8. **Traceability.** Cross-references (relations, source_refs) resolve
   against the ID index; no dangling relations are introduced.
9. **Generated artifacts marked.** `index.md` and other projections carry
   the generated-file marker and are not hand-edited.
10. **Test suite green.** `pytest -q` passes for the whole repository.

## Per-SPOC Definition of Done

See masterplan section 23 (reproduced here for convenience, not
duplicated):

- Schema/references valid; inputs and versions fixed in a run manifest.
- Agent/model/skill/tool selections recorded.
- Policy and access checks passed; required outputs at approved locations.
- Outputs pass schemas and quality gates; requirement traceability
  complete.
- Every acceptance criterion's linked test case executed by the QA agent
  with a passing test result (ADR-020).
- Material decisions/assumptions recorded; human approvals present where
  required.
- Run events and summary complete; Git changes reviewed and merged or
  explicitly rejected.
- Follow-up risks/issues/actions have owners; cost/resource usage
  recorded; SPOC in a terminal state.

The platform DoD governs *how we build the platform*; the per-SPOC DoD
governs *what a completed unit of platform-executed work looks like*.
