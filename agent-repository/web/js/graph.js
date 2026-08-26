"use strict";

/* Knowledge-graph view + document viewer (plan milestone M9.5).

Renders graph_index.json as an SVG with a type-colored legend, search and
filter controls, and a document viewer that opens any OKF node by its
stable id (deep links resolve by id, not by file path). */

const GraphView = (() => {
  let currentGraph = null;
  let currentStyle = null;

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));
  }

  function colorFor(type) {
    return (currentStyle && currentStyle[type] && currentStyle[type].color) || "#94a3b8";
  }

  async function render(container) {
    container.innerHTML = `<div class="panel"><h2>Knowledge graph</h2><div class="hint">Loading…</div></div>`;
    const [graph, style] = await Promise.all([
      Api.get("/api/v1/graph"),
      Api.get("/api/v1/graph/style").catch(() => ({ types: {} })),
    ]);
    currentGraph = graph;
    currentStyle = style.types || {};

    container.innerHTML = `
      <div class="panel">
        <h2>Knowledge graph</h2>
        <div class="legend" id="graph-legend"></div>
        <div style="margin-bottom:0.5rem">
          <input type="text" id="graph-search" placeholder="Search id/type/status/owner…">
          <select id="graph-filter-type"><option value="">all types</option></select>
        </div>
        <svg class="graph" id="graph-svg" viewBox="0 0 960 560" preserveAspectRatio="xMidYMid meet"></svg>
      </div>
      <div class="panel" id="doc-viewer"><h2>Document viewer</h2><p class="hint">Click a node to open its artifact.</p></div>`;

    draw(graph.nodes, graph.edges);
    buildLegend();
    buildFilter(graph.nodes);

    container.querySelector("#graph-search").addEventListener("input", (event) => {
      draw(filterNodes(event.target.value, container.querySelector("#graph-filter-type").value));
    });
    container.querySelector("#graph-filter-type").addEventListener("change", (event) => {
      draw(filterNodes(container.querySelector("#graph-search").value, event.target.value));
    });
  }

  function filterNodes(query, type) {
    const nodes = currentGraph.nodes.filter((n) => {
      if (type && n.type !== type) return false;
      if (!query) return true;
      const hay = `${n.id} ${n.type} ${n.status} ${n.owner} ${n.title}`.toLowerCase();
      return query.toLowerCase().split(/\s+/).every((t) => hay.includes(t));
    });
    const ids = new Set(nodes.map((n) => n.id));
    const edges = currentGraph.edges.filter((e) => ids.has(e.source) && ids.has(e.target));
    return { nodes, edges };
  }

  function buildLegend() {
    const types = [...new Set(currentGraph.nodes.map((n) => n.type))].sort();
    document.getElementById("graph-legend").innerHTML = types
      .map((t) => `<span class="item"><span class="dot" style="background:${colorFor(t)}"></span>${escapeHtml(t)}</span>`)
      .join("");
  }

  function buildFilter(nodes) {
    const types = [...new Set(nodes.map((n) => n.type))].sort();
    const select = document.getElementById("graph-filter-type");
    for (const type of types) {
      const option = document.createElement("option");
      option.value = type;
      option.textContent = type;
      select.appendChild(option);
    }
  }

  function draw(nodes, edges) {
    const svg = document.getElementById("graph-svg");
    if (!svg) return;
    const width = 960;
    const height = 560;
    const cx = width / 2;
    const cy = height / 2;
    const radius = Math.min(width, height) / 2 - 50;

    const positions = {};
    nodes.forEach((node, index) => {
      const angle = (index / Math.max(nodes.length, 1)) * 2 * Math.PI - Math.PI / 2;
      positions[node.id] = { x: cx + radius * Math.cos(angle), y: cy + radius * Math.sin(angle) };
    });

    const edgeLines = edges.map((edge) => {
      const s = positions[edge.source];
      const t = positions[edge.target];
      if (!s || !t) return "";
      return `<line class="edge" x1="${s.x}" y1="${s.y}" x2="${t.x}" y2="${t.y}"></line>`;
    }).join("");

    const nodeEls = nodes.map((node) => {
      const p = positions[node.id];
      return `<g class="node" data-node-id="${escapeHtml(node.id)}" style="cursor:pointer">
        <circle cx="${p.x}" cy="${p.y}" r="9" fill="${colorFor(node.type)}"></circle>
        <text x="${p.x + 13}" y="${p.y + 4}">${escapeHtml(node.id)}</text>
      </g>`;
    }).join("");

    svg.innerHTML = edgeLines + nodeEls;

    svg.querySelectorAll("g.node").forEach((group) => {
      group.addEventListener("click", () => openDocument(group.dataset.nodeId));
    });
  }

  async function openDocument(nodeId) {
    const viewer = document.getElementById("doc-viewer");
    if (!viewer) return;
    viewer.innerHTML = `<h2>Document viewer</h2><div class="hint">Loading ${escapeHtml(nodeId)}…</div>`;
    try {
      const artifact = await Api.get(`/api/v1/artifacts/${encodeURIComponent(nodeId)}`);
      const fm = artifact.front_matter || {};
      const relations = (fm.relations || [])
        .map((r) => `<span class="citation-link" data-node-id="${escapeHtml(r.target)}">${escapeHtml(r.type)} → ${escapeHtml(r.target)}</span>`)
        .join(" ");
      viewer.innerHTML = `
        <h2>${escapeHtml(nodeId)} <span class="hint">${escapeHtml(fm.type || "")} · ${escapeHtml(fm.status || "")}</span></h2>
        <p><strong>Title:</strong> ${escapeHtml(fm.title || "")}</p>
        <p><strong>Owner:</strong> ${escapeHtml(fm.owner || "")} · <strong>Classification:</strong> ${escapeHtml(fm.classification || "")}</p>
        <div><strong>Relations:</strong> ${relations || '<span class="hint">(none)</span>'}</div>
        <h3>Body</h3>
        <pre style="white-space:pre-wrap">${escapeHtml(artifact.body || "")}</pre>`;
      viewer.querySelectorAll(".citation-link").forEach((link) => {
        link.addEventListener("click", () => openDocument(link.dataset.nodeId));
      });
    } catch (error) {
      viewer.innerHTML = `<h2>Document viewer</h2><p class="issues">${escapeHtml(error.message)}</p>`;
    }
  }

  return { render, openDocument };
})();
