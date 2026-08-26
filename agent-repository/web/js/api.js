"use strict";

/* Minimal API client. All data comes from the control-plane REST API;
   the UI never bypasses policy or the graph (ADR-023). */

const Api = (() => {
  let token = localStorage.getItem("mas-token") || "";

  function setToken(value) {
    token = value;
    if (value) localStorage.setItem("mas-token", value);
    else localStorage.removeItem("mas-token");
  }

  function getToken() {
    return token;
  }

  async function request(method, path, body) {
    const headers = { "Content-Type": "application/json" };
    if (token) headers["Authorization"] = `Bearer ${token}`;
    const response = await fetch(path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
    if (response.status === 204) return null;
    const text = await response.text();
    const data = text ? JSON.parse(text) : null;
    if (!response.ok) {
      const error = new Error(data && data.detail ? data.detail : `HTTP ${response.status}`);
      error.status = response.status;
      throw error;
    }
    return data;
  }

  return {
    setToken,
    getToken,
    get: (path) => request("GET", path),
    post: (path, body) => request("POST", path, body),
  };
})();
