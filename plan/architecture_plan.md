MASTER ARCHITECTURE PLAN & IMPLEMENTATION SPECIFICATION
File Name: master_architecture_plan.md

System: Enterprise Multi-Agent Engine (OKF + SPOC + Capability Matching)

Standard: Open Knowledge Format (OKF) v1.0 & SPOC Contract Protocol

Target Audience: Lead Software Architect / Automated Coding Agent

1. EXECUTIVE SUMMARY & SYSTEMPRINZIPIEN

Dieses Dokument ist die vollständige, monolithische Architektur- und Implementierungsspezifikation für ein hochskalierbares Multi-Agenten-System. Das System basiert auf vier fundamentalen Entwurfsprinzipien:

Entkoppelte Drei-Repository-Topologie: Strikt getrennte Verwaltung von Agenten-Infrastruktur (agent-repository), Governance/Blueprints (project-template-repository) und Laufzeit-Projektdaten (active-project-repo).

Open Knowledge Format (OKF): Sämtliche Artefakte (Anforderungen, Spezifikationen, Logs, Wissen) werden als atomare Markdown-Dateien mit standardisiertem YAML-Frontmatter gespeichert und zu einem gerichteten Wissensgraphen vernetzt.

SPOC-Vertragssystem (Supplier-Procedure-Output-Consumer): Jede Aufgabe wird über einen deterministischen Schnittstellenvertrag definiert, der Eingaben, Ausführungsregeln, Qualitätskriterien und Ziel-Konsumenten festlegt.

Capability Matching & Agent-as-a-Tool: Agenten werden nicht fest verdrahtet, sondern zur Laufzeit anhand von benötigten Capabilities (explizit und implizit) dynamisch gewählt. Fehlen dem gewählten Primär-Agenten Teilfähigkeiten, werden Spezial-Agenten automatisch als aufrufbare Tools (Agent-as-a-Tool) gekapselt und übergeben.

2. DREI-REPOSITORY-TOPOLOGIE & VERZEICHNISSTRUKTUREN

2.1 Repo A: agent-repository (Infrastruktur, Tools & Registry)

registry/: Zentrale Agenten-Registry & Skill-Verzeichnis

capabilities_index.yaml: Übersicht aller vergebenen Capabilities

sme_security/: Agent Profile (config.yaml) & private_knowledge/ (pattern_auth0_bugs.md, index.md)

controller_finances/: Agent Profile (config.yaml) & private_knowledge/ (risk_cost_ratios.md, index.md)

qa_evaluator/: Agent Profile (config.yaml) & private_knowledge/ (quality_gates.md)

public_knowledge/: Globales, projektübergreifendes Freiwissen (guidelines/security_policy.md, coding_standards.md)

tools/: Tool-Bibliothek & MCP Integrations (custom_tools/github_tools.py, okf_linter.py, file_tools.py, mcp_configs/mcp_servers.json)

2.2 Repo B: project-template-repository (Blueprints & Governance)

templates/spocs/: Standard-SPOC Templates im OKF-Format (spoc_feature_template.md, spoc_qa_template.md)

templates/user_stories/: Anforderungs-Templates (user_story_template.md)

templates/compliance/: Regulatorik & QA-Checklisten (quality_gate_rules.md, iso_security_rules.md)

workflows/: Standard-Prozessketten (default_feature_pipeline.yaml)

2.3 Repo C: active-project-repo (Laufzeit-Projekt)

.vscode/: VS Code Integration & MCP Config (settings.json, mcp.json)

public/: ÖFFENTLICHER BEREICH (Lesbar für alle Agenten)

user_stories/: Projekt-Anforderungen (US-001-oauth.md)

spocs/: Aktive & abgearbeitete SPOCs im OKF-Format (SPOC-2026-001.md, index.md)

okf_knowledge/: Projektweiter Wissensgraph (specs/auth_concept.md, index.md)

private/: PRIVATER BEREICH (Isolierte Agenten-Workspaces)

sme_security/: Schreib-/Lesebereich (scratchpad_draft.json)

controller_finances/: Schreib-/Lesebereich (raw_calculations.json)

logs/: Lückenloses Audit Logging (spoc_execution_log.md, index.md)

3. OPEN KNOWLEDGE FORMAT (OKF) SPEZIFIKATION

Jede Wissensdatei, SPOC-Definition, User Story und Log-Eintrag MUSS dem OKF-Standard entsprechen.

3.1 OKF Standard Frontmatter Schema
Jede Datei beginnt mit folgendem Header:

id: "OKF-DOC-2026-089"

type: "concept" (Optionen: concept | specification | spoc | guideline | log)

title: "OAuth2 Architektur-Spezifikation"

description: "Spezifikation der OAuth2-Tokens, Datenbankanpassung und Security-Richtlinien."

created_at: "2026-08-22"

updated_at: "2026-08-22"

stale_after: "2026-12-31"

owner: "sme_security"

tags: ["auth", "security", "oauth2"]

cross_references: ["../guidelines/security_policy.md", "../specs/user_db.md"]

3.2 OKF Linter Implementierung (agent-repository/tools/custom_tools/okf_linter.py)

Code: okf_linter.py

import os, re, yaml

from typing import List, Tuple

REQUIRED_FRONTMATTER_KEYS = {"id", "type", "title", "description", "created_at", "owner"}

def validate_okf_file(file_path: str) -> Tuple[bool, List[str]]:

    errors = []

    if not file_path.endswith('.md'): return True, []

    with open(file_path, 'r', encoding='utf-8') as f:

        content = f.read()

    frontmatter_match = re.match(r'^---\s*\n(.*?)\n---\s*\n', content, re.DOTALL)

    if not frontmatter_match:

        errors.append(f"Fehlendes Frontmatter in {file_path}")

        return False, errors

    try:

        data = yaml.safe_load(frontmatter_match.group(1))

        missing_keys = REQUIRED_FRONTMATTER_KEYS - set(data.keys())

        if missing_keys: errors.append(f"Fehlende Pflichtfelder: {missing_keys}")

    except Exception as e:

        errors.append(f"YAML Parsing Fehler: {str(e)}")

    links = re.findall(r'\[.*?\]\((.*?\.md)\)', content)

    base_dir = os.path.dirname(file_path)

    for link in links:

        target_path = os.path.normpath(os.path.join(base_dir, link))

        if not os.path.exists(target_path):

            errors.append(f"Defekter Link: '{link}' -> Ziel '{target_path}' existiert nicht.")

    return len(errors) == 0, errors

4. SPOC FRAMEWORK (SUPPLIER-PROCEDURE-OUTPUT-CONSUMER)

SPOCs definieren jede Aufgabe als strukturierte Schnittstellenvereinbarung (public/spocs/SPOC-YYYY-XXX.md).

Metadata: id: "SPOC-2026-010" | type: "spoc" | status: "pending" | required_capabilities: ["oauth2_design", "okf_curation"] | model_override: "gpt-4o"

Supplier: Source Paths: public/user_stories/US-001-oauth.md, public_knowledge/guidelines/security_policy.md | Provided By: projektleiter

Procedure: Analysiere die Anforderungen aus US-001 und erstelle eine technische Spezifikation. Achte strikt auf die Einhaltung der globalen Security Policy. Erstelle bei Budgetfragen eine Anfrage an den Financial Controller Agenten.

Output: Target Path: public/okf_knowledge/specs/auth_concept.md | Format: OKF Concept Document | Validation Schema: okf_concept_v1

Consumer: Target Agent: qa_agent | On Success: Trigger Quality Gate / Git PR | On Reject: Return to Supplier

5. AGENT CONFIGURATION & CAPABILITY MATCHING ENGINE

5.1 Agent Configuration Schema (agent-repository/registry/<agent_id>/config.yaml)

agent_id: "sme_security"

name: "Security SME Agent"

role: "Security & Compliance Specialist"

backstory: "Experte für OAuth2, Verschlüsselung und Enterprise Security."

default_model: "gpt-4o"

capabilities: ["oauth2_design", "security_audit", "okf_curation"]

assigned_tools: ["file_writer_tool", "github_commit_tool"]

private_workspace: "private/sme_security/"

global_experience_path: "registry/sme_security/private_knowledge/"

5.2 Capability Matching & Agent-as-a-Tool Engine (agent-repository/tools/capability_matcher.py)

Code: capability_matcher.py

import os, yaml, re

from typing import List, Dict, Any

from crewai import Agent, Task, Crew

from crewai.tools import tool

class CapabilityMatcher:

    def __init__(self, registry_base_path: str):

        self.registry_base_path = registry_base_path

        self.agents_db = self._load_agent_registry()

    def _load_agent_registry(self) -> List[Dict[str, Any]]:

        agents = []

        for root, dirs, files in os.walk(self.registry_base_path):

            if "config.yaml" in files:

                with open(os.path.join(root, "config.yaml"), "r", encoding="utf-8") as f:

                    agents.append(yaml.safe_load(f))

        return agents

    def match_spoc(self, spoc_frontmatter: Dict[str, Any], procedure_text: str) -> Dict[str, Any]:

        explicit_caps = set(spoc_frontmatter.get("required_capabilities", []))

        implicit_caps = self._infer_implicit_capabilities(procedure_text)

        all_required_caps = explicit_caps.union(implicit_caps)

        best_agent, max_matches = None, -1

        for agent in self.agents_db:

            provided = set(agent.get("capabilities", []))

            matches = len(all_required_caps.intersection(provided))

            if matches > max_matches:

                max_matches, best_agent = matches, agent

        if not best_agent: raise RuntimeError("Kein Agent gefunden.")

        missing_caps = all_required_caps - set(best_agent.get("capabilities", []))

        sub_agent_tools = []

        for cap in missing_caps:

            sub_config = self._find_agent_for_capability(cap)

            if sub_config: sub_agent_tools.append(self.wrap_agent_as_tool(sub_config))

        return {

            "primary_agent": best_agent,

            "sub_agent_tools": sub_agent_tools,

            "model_override": spoc_frontmatter.get("model_override") or best_agent.get("default_model")

        }

    def _infer_implicit_capabilities(self, procedure_text: str) -> set:

        inferred = set()

        if re.search(r'budget|finanz|kosten|preis', procedure_text, re.I): inferred.add("financial_analysis")

        if re.search(r'sicherheit|dsgvo|gdpr|encryption', procedure_text, re.I): inferred.add("security_audit")

        return inferred

    def _find_agent_for_capability(self, cap: str) -> Dict[str, Any]:

        for agent in self.agents_db:

            if cap in agent.get("capabilities", []): return agent

        return None

    def wrap_agent_as_tool(self, agent_config: Dict[str, Any]):

        sub_agent = Agent(role=agent_config["role"], goal=f"Beantworte Anfragen zu {agent_config['agent_id']}", backstory=agent_config["backstory"], verbose=False)

        @tool(f"ask_{agent_config['agent_id']}")

        def agent_tool(query: str) -> str:

            task = Task(description=f"Spezialaufgabe: {query}", expected_output="Geprüfte Antwort.", agent=sub_agent)

            return str(Crew(agents=[sub_agent], tasks=[task]).kickoff())

        return agent_tool

6. STRICT AUDIT LOGGING ENGINE (logs/spoc_execution_log.md)

Code: audit_logger.py

import os

from datetime import datetime

class AuditLogger:

    def __init__(self, log_path: str = "logs/spoc_execution_log.md"):

        self.log_path = log_path

        os.makedirs(os.path.dirname(self.log_path), exist_ok=True)

    def append_log(self, spoc_id: str, primary_agent: str, sub_agents: list, llm_model: str, human_in_loop: bool, inputs: list, outputs: list, traces: list):

        timestamp = datetime.utcnow().isoformat() + "Z"

        sub_agents_str = ", ".join([f"'{a}'" for a in sub_agents]) if sub_agents else "None"

        entry = f"\n## [{timestamp}] EXECUTION LOG: {spoc_id}\n"

        entry += f"- **Primary Agent:** '{primary_agent}'\n"

        entry += f"- **Sub-Agents:** {sub_agents_str}\n"

        entry += f"- **LLM Model:** '{llm_model}'\n"

        entry += f"- **Human in Loop:** {human_in_loop}\n"

        entry += f"- **Inputs:** {', '.join(inputs)}\n"

        entry += f"- **Outputs:** {', '.join(outputs)}\n\n### Trace:\n"

        for idx, trace in enumerate(traces, 1): entry += f"{idx}. {trace}\n"

        entry += "\n---\n"

        with open(self.log_path, "a", encoding="utf-8") as f: f.write(entry)

7. VS CODE & MODEL CONTEXT PROTOCOL (MCP) INTEGRATION

7.1 MCP Konfiguration (.vscode/mcp.json)

filesystem: Command: npx | Args: ["-y", "@modelcontextprotocol/server-filesystem", "./public", "./private"]

git: Command: python | Args: ["-m", "mcp_server_git", "--repository", "."]

7.2 Laufzeit-Agenten-Generator (agent-repository/tools/create_new_agent.py)

Code: create_new_agent.py

import sys, os, yaml

def generate_agent(agent_id: str, role: str, capabilities_str: str):

    capabilities = [c.strip() for c in capabilities_str.split(",")]

    agent_dir = os.path.join("registry", agent_id)

    os.makedirs(os.path.join(agent_dir, "private_knowledge"), exist_ok=True)

    config = {

        "agent_id": agent_id, "name": f"{role} Agent", "role": role,

        "backstory": f"Autonom erstellter Spezialist für {role}.",

        "default_model": "gpt-4o", "capabilities": capabilities, "assigned_tools": ["file_writer_tool"]

    }

    with open(os.path.join(agent_dir, "config.yaml"), "w", encoding="utf-8") as f:

        yaml.dump(config, f, allow_unicode=True)

    with open(os.path.join(agent_dir, "private_knowledge", "index.md"), "w", encoding="utf-8") as f:

        f.write(f"# Private Knowledge Index: {agent_id}\n\n- No documents yet.\n")

    print(f"Agent '{agent_id}' angelegt.")

if __name__ == "__main__":

    if len(sys.argv) < 4: sys.exit(1)

    generate_agent(sys.argv[1], sys.argv[2], sys.argv[3])

8. WEB UI & REST/SSE API LAYER (server/app.py)

Code: app.py

import asyncio

from fastapi import FastAPI, BackgroundTasks

from fastapi.responses import StreamingResponse

app = FastAPI(title="Multi-Agent OKF/SPOC Engine")

@app.get("/api/v1/agents")

def list_registry_agents(): return {"status": "success", "agents": []}

@app.post("/api/v1/spocs/execute")

def trigger_spoc_execution(spoc_id: str, background_tasks: BackgroundTasks):

    return {"status": "queued", "spoc_id": spoc_id}

@app.get("/api/v1/logs/stream")

async def stream_audit_logs():

    async def log_event_generator():

        while True:

            await asyncio.sleep(2)

            yield 'data: {"type": "heartbeat"}\n\n'

    return StreamingResponse(log_event_generator(), media_type="text/event-stream")

9. SCHRITT-FÜR-SCHRITT IMPLEMENTIERUNGS-ROADMAP

Phase 1: Repository Setup & Skeleton Layout – Erstelle Ordnerstrukturen für Repo A, B und C. Richte .vscode/mcp.json ein.

Phase 2: OKF Validation & Linter Tooling – Implementiere okf_linter.py zur Prüfung von Frontmatter und Verlinkungen.

Phase 3: Capability Matcher & Agent-as-a-Tool Engine – Implementiere CapabilityMatcher und den dynamischen Sub-Agent-Wrapper.

Phase 4: SPOC Runner & Audit Logging Engine – Baue SpocRunner zur Orchestrierung und AuditLogger für logs/spoc_execution_log.md.

Phase 5: API Layer & End-to-End Testlauf – Starte FastAPI Server (server/app.py) und führe den vollständigen E2E-Durchlauf aus.