"""Project Manager conversational query flow (masterplan section 13.6,
11.4, plan milestone M9.3).

A read-only, session-scoped query flow distinct from the project
execution flow::

    load_session_state -> authorize_query_scope -> query_graph_and_evidence
    -> compose_grounded_answer -> attach_citations -> log_chat_event -> end

It only reads the public knowledge graph and run evidence. It never
writes artifacts, never triggers ``execute_bounded_crews``, and never
mutates approvals or project state. Every substantive answer cites the
OKF ``id`` of the artifacts it used; an ungrounded answer says so instead
of fabricating one.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from agent_platform.application.ports.clock_and_ids import Clock, IdGenerator
from agent_platform.application.ports.event_ledger import EventLedger
from agent_platform.application.ports.policy_decision_point import PolicyDecisionPoint
from agent_platform.domain.events import Actor, RunEvent
from agent_platform.schemas.canonicalize import load_okf_file

# Classification the PM agent may read by default (masterplan section
# 11.4): public + internal; confidential/restricted denied by default.
DEFAULT_ALLOWED_CLASSIFICATIONS = ("public", "internal")

MAX_CITATIONS = 5


@dataclass(frozen=True)
class ChatMessage:
    role: str
    content: str
    citations: list[str] = field(default_factory=list)


@dataclass
class ChatSession:
    session_id: str
    project_id: str
    classification: str
    created_at: str
    messages: list[ChatMessage] = field(default_factory=list)


@dataclass(frozen=True)
class ChatAnswer:
    session_id: str
    answer: str
    citations: list[str]
    grounded: bool
    authorized: bool = True


@dataclass
class PmQueryFlow:
    policy: PolicyDecisionPoint
    graph_index: dict | None = None
    project_root: Path | None = None
    event_ledger: EventLedger | None = None
    id_generator: IdGenerator | None = None
    clock: Clock | None = None
    allowed_classifications: tuple[str, ...] = DEFAULT_ALLOWED_CLASSIFICATIONS
    _sessions: dict[str, ChatSession] = field(default_factory=dict)

    # -- session lifecycle --------------------------------------------------

    def create_session(
        self, *, session_id: str, project_id: str, classification: str = "internal"
    ) -> ChatSession:
        session = ChatSession(
            session_id=session_id,
            project_id=project_id,
            classification=classification,
            created_at=self._now(),
        )
        self._sessions[session_id] = session
        return session

    def get_session(self, session_id: str) -> ChatSession:
        return self._sessions[session_id]

    # -- query flow -----------------------------------------------------------

    def ask(self, session_id: str, question: str) -> ChatAnswer:
        # 1. load_session_state
        session = self._sessions.get(session_id)
        if session is None:
            raise KeyError(f"unknown chat session '{session_id}'")

        # 2. authorize_query_scope (classification-aware, masterplan 11.4).
        # The default-allow list is enforced locally (defense in depth),
        # then the injected policy decision point is consulted as an
        # additional gate.
        if session.classification not in self.allowed_classifications:
            answer = ChatAnswer(
                session_id=session_id,
                answer=(
                    f"I cannot answer from {session.classification}-classified project data; "
                    "that classification is denied by default."
                ),
                citations=[],
                grounded=False,
                authorized=False,
            )
            self._log(session, question, answer)
            return answer

        decision = self.policy.evaluate(
            action="chat_query",
            context={
                "classification": session.classification,
                "allowed_classifications": list(self.allowed_classifications),
            },
        )
        if not decision.allowed:
            answer = ChatAnswer(
                session_id=session_id,
                answer=(
                    f"I cannot answer from {session.classification}-classified project data: "
                    f"{decision.reason}."
                ),
                citations=[],
                grounded=False,
                authorized=False,
            )
            self._log(session, question, answer)
            return answer

        # 3. query_graph_and_evidence
        matches = self._query_graph(question)

        # 4. compose_grounded_answer
        if not matches:
            answer = ChatAnswer(
                session_id=session_id,
                answer=(
                    "I don't have enough grounded evidence to answer that question; "
                    "I'd rather say so than fabricate an answer."
                ),
                citations=[],
                grounded=False,
            )
        else:
            lines = [self._compose_line(match) for match in matches[:MAX_CITATIONS]]
            answer = ChatAnswer(
                session_id=session_id,
                answer="Based on the project graph: " + "; ".join(lines) + ".",
                citations=[m["id"] for m in matches[:MAX_CITATIONS]],
                grounded=True,
            )

        # 5. attach_citations is folded into ChatAnswer.citations
        # 6. log_chat_event
        self._log(session, question, answer)
        return answer

    # -- internal -----------------------------------------------------------

    def _now(self) -> str:
        return self.clock.now_iso() if self.clock is not None else "1970-01-01T00:00:00Z"

    def _query_graph(self, question: str) -> list[dict]:
        if not self.graph_index:
            return []
        tokens = {t.lower() for t in question.replace("?", " ").replace(".", " ").split() if len(t) > 2}
        if not tokens:
            return []

        scored: list[tuple[int, dict]] = []
        allowed = set(self.allowed_classifications)
        for node in self.graph_index.get("nodes", []):
            if node.get("classification", "internal") not in allowed:
                continue
            haystack = " ".join(
                str(node.get(key, "")).lower()
                for key in ("id", "type", "status", "owner", "title", "classification")
            )
            haystack += " " + " ".join(str(r).lower() for r in node.get("source_refs", []))
            score = sum(1 for t in tokens if t in haystack)
            if score > 0:
                scored.append((score, node))

        scored.sort(key=lambda pair: (-pair[0], pair[1].get("id", "")))
        return [node for _, node in scored]

    def _compose_line(self, node: dict) -> str:
        return f"{node.get('id')} ({node.get('type')}, {node.get('status')})"

    def _log(self, session: ChatSession, question: str, answer: ChatAnswer) -> None:
        session.messages.append(ChatMessage(role="user", content=question))
        session.messages.append(
            ChatMessage(role="assistant", content=answer.answer, citations=answer.citations)
        )
        if self.event_ledger is not None:
            self.event_ledger.append(
                RunEvent(
                    event_id=self.id_generator.new_id("evt") if self.id_generator else "chat-evt",
                    run_id=session.session_id,
                    attempt_id=session.session_id,
                    aggregate_id=session.session_id,
                    event_type="chat_message",
                    timestamp=self._now(),
                    actor=Actor(type="agent", id="project_manager_agent"),
                    payload={
                        "role": "assistant",
                        "grounded": answer.grounded,
                        "citations": answer.citations,
                        "classification": session.classification,
                    },
                )
            )


def read_artifact_body(project_root: Path, node: dict) -> str | None:
    """Read the Markdown body of an OKF node (by relative path) for
    grounding snippets. Returns None if the file is unavailable."""
    path = node.get("path")
    if not path or project_root is None:
        return None
    try:
        return load_okf_file(Path(project_root) / path).body
    except Exception:  # noqa: BLE001 - missing/unparsable artifact is not fatal to grounding
        return None
