# Web UI

A dependency-free, static single-page client served by the control plane
(ADR-023). It is a client of the same REST API and never bypasses policy
or the graph.

## Structure

- `index.html` — shell with the sidebar, token control, and view container.
- `css/app.css` — styling and the graph legend.
- `js/api.js` — fetch wrapper with bearer token.
- `js/okf-validator.js` — focused JSON-Schema-subset validator used by the
  SPOC editor against the backend-served `spoc.schema.json`.
- `js/views.js` — overview, SPOC editor, runs, approvals, registry views.
- `js/graph.js` — knowledge-graph SVG view, legend, search/filter, and the
  document viewer (deep links by stable OKF `id`).
- `js/chat.js` — the persistent Project Manager chat panel (mounted on
  every screen; citations link into the document viewer).
- `js/app.js` — hash router and bootstrap.

## Running

```text
uvicorn agent_platform.api.main:app
# then open http://127.0.0.1:8000/
```

Set the bearer token in the sidebar (dev default: `dev-token-admin`).

## Single source of truth

The SPOC editor fetches `GET /api/v1/schemas/spoc.schema.json` and
validates against it client-side; the backend re-validates on every
mutating call. There is no vendored schema copy to drift.
