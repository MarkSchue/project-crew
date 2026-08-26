"use strict";

/* Project overview, SPOC editor, runs, approvals, and registry views
   (plan milestone M9.4). Each view renders into its container and binds
   its own events. All data flows through the REST API. */

const Views = (() => {
  function badge(status) {
    let cls = "";
    if (["closed", "accepted", "approved", "active"].includes(status)) cls = "ok";
    else if (["blocked", "dead_letter", "rejected", "expired", "open"].includes(status)) cls = "warn";
    return `<span class="badge ${cls}">${escapeHtml(status || "")}</span>`;
  }

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));
  }

  // -- overview ---------------------------------------------------------

  async function renderOverview(container) {
    container.innerHTML = `<div class="panel"><h2>Project overview</h2><div class="hint">Loading…</div></div>`;
    const [graph, runs] = await Promise.all([
      Api.get("/api/v1/graph"),
      Api.get("/api/v1/runs"),
    ]);

    const byType = {};
    const byStatus = {};
    for (const node of graph.nodes) {
      byType[node.type] = (byType[node.type] || 0) + 1;
      byStatus[node.status] = (byStatus[node.status] || 0) + 1;
    }

    container.innerHTML = `
      <div class="panel"><h2>Project overview</h2>
        <p class="hint">${graph.nodes.length} graph nodes · ${graph.edges.length} relations</p>
        <h3>Nodes by type</h3>
        <table><tr><th>type</th><th>count</th></tr>
        ${Object.entries(byType).sort().map(([k, v]) => `<tr><td>${escapeHtml(k)}</td><td>${v}</td></tr>`).join("")}
        </table>
      </div>
      <div class="panel"><h2>Runs</h2>
        <table><tr><th>run</th><th>project</th><th>status</th></tr>
        ${runs.items.map((r) => `<tr><td>${escapeHtml(r.run_id)}</td><td>${escapeHtml(r.project_id)}</td><td>${badge(r.status)}</td></tr>`).join("") || `<tr><td colspan="3" class="hint">No runs yet.</td></tr>`}
        </table>
      </div>`;
  }

  // -- SPOC editor -------------------------------------------------------

  const SAMPLE_SPOC = {
    schema_version: "spoc/1.1",
    id: "SPOC-DEMO-001",
    type: "spoc",
    title: "Demo SPOC",
    status: "draft",
    project_id: "PRJ-001",
    owner: "project_manager",
    created_at: "2026-08-26T09:00:00Z",
    classification: "internal",
    workflow: "requirement_to_delivery@1.2.0",
    supplier: { provided_by: "product_owner", inputs: [{ ref: "public/user_stories/US-001.md", required: true }] },
    procedure: { objective: "demo", explicit_capabilities: ["architecture.solution_documentation"] },
    output: {
      artifacts: [{ target: "public/deliverables/DEL-DEMO.md", schema: "okf/1.1", required: true }],
      acceptance_criteria: [{ id: "AC-1", statement: "demo accepted", validator: "traceability_validator" }],
    },
    consumer: { next_role: "qa_agent", on_success: "request_human_approval", on_reject: "return_to_originating_agent" },
    retry_policy: { max_attempts: 2, retry_on: ["schema_validation_error"] },
  };

  async function renderSpocEditor(container) {
    container.innerHTML = `<div class="panel"><h2>SPOC editor</h2><div class="hint">Loading schema…</div></div>`;
    const schema = await Api.get("/api/v1/schemas/spoc.schema.json");

    container.innerHTML = `
      <div class="panel">
        <h2>SPOC editor</h2>
        <p class="hint">Validated client-side against <code>spoc.schema.json</code> fetched from the backend (single source of truth).</p>
        <textarea id="spoc-editor-input">${escapeHtml(JSON.stringify(SAMPLE_SPOC, null, 2))}</textarea>
        <div style="margin-top:0.5rem">
          <button id="spoc-validate-client">Validate (client)</button>
          <button id="spoc-validate-backend" class="secondary">Validate (backend)</button>
        </div>
        <div id="spoc-issues" class="issues"></div>
      </div>`;

    const input = container.querySelector("#spoc-editor-input");
    const issues = container.querySelector("#spoc-issues");

    function parse() {
      try {
        return JSON.parse(input.value);
      } catch (error) {
        issues.textContent = `Invalid JSON: ${error.message}`;
        return null;
      }
    }

    container.querySelector("#spoc-validate-client").addEventListener("click", () => {
      const value = parse();
      if (value === null) return;
      const errors = OkfValidator.validate(schema, value);
      if (errors.length === 0) {
        issues.innerHTML = `<span class="badge ok">valid</span>`;
      } else {
        issues.textContent = errors.join("\n");
      }
    });

    container.querySelector("#spoc-validate-backend").addEventListener("click", async () => {
      const value = parse();
      if (value === null) return;
      try {
        const result = await Api.post("/api/v1/spocs/validate", { spoc: value });
        issues.innerHTML = result.valid
          ? `<span class="badge ok">backend: valid</span>`
          : `<span class="badge danger">backend: invalid</span>\n${result.issues.join("\n")}`;
      } catch (error) {
        issues.textContent = `Backend validation failed: ${error.message}`;
      }
    });
  }

  // -- runs ---------------------------------------------------------------

  async function renderRuns(container) {
    container.innerHTML = `<div class="panel"><h2>Runs</h2><div class="hint">Loading…</div></div>`;
    const runs = await Api.get("/api/v1/runs");
    container.innerHTML = `
      <div class="panel"><h2>Runs</h2>
        <table><tr><th>run</th><th>project</th><th>status</th></tr>
        ${runs.items.map((r) => `<tr><td>${escapeHtml(r.run_id)}</td><td>${escapeHtml(r.project_id)}</td><td>${badge(r.status)}</td></tr>`).join("") || `<tr><td colspan="3" class="hint">No runs.</td></tr>`}
        </table>
      </div>`;
  }

  // -- approvals -----------------------------------------------------------

  async function renderApprovals(container) {
    container.innerHTML = `<div class="panel"><h2>Approval inbox</h2><div class="hint">Loading…</div></div>`;
    const approvals = await Api.get("/api/v1/approvals");
    container.innerHTML = `
      <div class="panel"><h2>Approval inbox</h2>
        <table><tr><th>approval</th><th>scope</th><th>subject</th><th>status</th></tr>
        ${approvals.items.map((a) => `<tr><td>${escapeHtml(a.approval_id)}</td><td>${escapeHtml(a.scope)}</td><td>${escapeHtml(a.subject)}</td><td>${badge(a.status)}</td></tr>`).join("") || `<tr><td colspan="4" class="hint">No approval requests.</td></tr>`}
        </table>
      </div>`;
  }

  // -- registry ------------------------------------------------------------

  async function renderRegistry(container) {
    container.innerHTML = `<div class="panel"><h2>Registry</h2><div class="hint">Loading…</div></div>`;
    const [agents, capabilities] = await Promise.all([
      Api.get("/api/v1/registry/agents"),
      Api.get("/api/v1/registry/capabilities"),
    ]);
    container.innerHTML = `
      <div class="panel"><h2>Agents</h2>
        <table><tr><th>agent</th><th>status</th><th>capabilities</th></tr>
        ${agents.items.map((a) => `<tr><td>${escapeHtml(a.agent_id)}</td><td>${badge(a.status)}</td><td>${escapeHtml(a.capabilities.join(", "))}</td></tr>`).join("")}
        </table>
      </div>
      <div class="panel"><h2>Capabilities</h2>
        <table><tr><th>id</th><th>risk</th></tr>
        ${capabilities.items.map((c) => `<tr><td>${escapeHtml(c.id)}</td><td>${escapeHtml(c.risk_level)}</td></tr>`).join("")}
        </table>
      </div>`;
  }

  return {
    renderOverview,
    renderSpocEditor,
    renderRuns,
    renderApprovals,
    renderRegistry,
  };
})();
