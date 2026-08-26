"use strict";

/* Hash router + bootstrap. Mounts the persistent chat panel on every
   screen (M9.6) and routes the main view container. */

const App = (() => {
  const routes = {
    overview: Views.renderOverview,
    "spoc-editor": Views.renderSpocEditor,
    runs: Views.renderRuns,
    approvals: Views.renderApprovals,
    registry: Views.renderRegistry,
    graph: GraphView.render,
  };

  const DEFAULT_ROUTE = "overview";

  function currentRoute() {
    const hash = window.location.hash.replace(/^#\/?/, "");
    return routes[hash] ? hash : DEFAULT_ROUTE;
  }

  async function render() {
    const route = currentRoute();
    document.querySelectorAll("nav.sidebar a").forEach((link) => {
      link.classList.toggle("active", link.dataset.route === route);
    });
    const container = document.getElementById("view");
    container.innerHTML = `<div class="panel"><h2>Loading…</h2></div>`;
    try {
      await routes[route](container);
    } catch (error) {
      container.innerHTML = `<div class="panel"><h2>Error</h2><p class="issues">${error.message}</p>
        <p class="hint">Set your bearer token below and try again.</p></div>`;
    }
  }

  function bootstrap() {
    const nav = document.getElementById("nav");
    const labels = {
      overview: "Overview",
      "spoc-editor": "SPOC editor",
      runs: "Runs",
      approvals: "Approvals",
      registry: "Registry",
      graph: "Knowledge graph",
    };
    nav.innerHTML = Object.entries(labels)
      .map(([route, label]) => `<a href="#/${route}" data-route="${route}">${label}</a>`)
      .join("");

    const tokenInput = document.getElementById("token-input");
    tokenInput.value = Api.getToken();
    document.getElementById("token-save").addEventListener("click", () => {
      Api.setToken(tokenInput.value.trim());
      render();
    });

    window.addEventListener("hashchange", render);
    Chat.mount();
    render();
  }

  return { bootstrap };
})();

document.addEventListener("DOMContentLoaded", App.bootstrap);
