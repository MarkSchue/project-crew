"use strict";

/* Persistent Project Manager chat panel (plan milestone M9.6), mounted
   globally. Backed by the M9.2/M9.3 chat API; citations are rendered as
   clickable links into the graph/document viewer. */

const Chat = (() => {
  let sessionId = null;
  let classification = "internal";

  function escapeHtml(value) {
    return String(value ?? "").replace(/[&<>"']/g, (ch) => ({
      "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;",
    }[ch]));
  }

  function mount() {
    if (document.getElementById("chat-panel")) return;
    const panel = document.createElement("div");
    panel.className = "chat-panel";
    panel.id = "chat-panel";
    panel.innerHTML = `
      <header id="chat-header">Project Manager (collapsed)</header>
      <div class="messages" id="chat-messages" style="display:none"></div>
      <form id="chat-form" style="display:none">
        <select id="chat-classification">
          <option value="internal">internal</option>
          <option value="public">public</option>
          <option value="confidential">confidential</option>
          <option value="restricted">restricted</option>
        </select>
        <input type="text" id="chat-input" placeholder="Ask about project state…" autocomplete="off">
        <button type="submit">Send</button>
      </form>`;
    document.body.appendChild(panel);

    const header = panel.querySelector("#chat-header");
    const messages = panel.querySelector("#chat-messages");
    const form = panel.querySelector("#chat-form");

    header.addEventListener("click", () => {
      const open = messages.style.display !== "none";
      messages.style.display = open ? "none" : "block";
      form.style.display = open ? "none" : "flex";
      header.textContent = open ? "Project Manager (collapsed)" : "Project Manager";
    });

    panel.querySelector("#chat-classification").addEventListener("change", (event) => {
      classification = event.target.value;
    });

    form.addEventListener("submit", async (event) => {
      event.preventDefault();
      const input = panel.querySelector("#chat-input");
      const question = input.value.trim();
      if (!question) return;
      input.value = "";
      await send(question);
    });
  }

  function addMessage(role, text, citations) {
    const messages = document.getElementById("chat-messages");
    if (!messages) return;
    const div = document.createElement("div");
    div.className = "msg";
    const label = role === "user" ? `<span class="user">You:</span> ` : `<strong>PM:</strong> `;
    div.innerHTML = label + escapeHtml(text);
    if (citations && citations.length) {
      const cite = document.createElement("div");
      cite.className = "citations";
      cite.innerHTML = "citations: " + citations
        .map((c) => `<span class="citation-link" data-node-id="${escapeHtml(c)}">${escapeHtml(c)}</span>`)
        .join(" ");
      cite.querySelectorAll(".citation-link").forEach((link) => {
        link.addEventListener("click", () => GraphView.openDocument(link.dataset.nodeId));
      });
      div.appendChild(cite);
    }
    messages.appendChild(div);
    messages.scrollTop = messages.scrollHeight;
  }

  async function send(question) {
    if (!sessionId) {
      const session = await Api.post("/api/v1/chat/sessions", {
        project_id: "PRJ-001",
        classification,
      });
      sessionId = session.session_id;
    }
    addMessage("user", question);
    const answer = await Api.post(`/api/v1/chat/sessions/${sessionId}/messages`, { content: question });
    addMessage("assistant", answer.answer, answer.citations);
  }

  return { mount, send };
})();
