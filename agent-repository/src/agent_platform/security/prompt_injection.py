"""Prompt-injection detection for untrusted repository content (masterplan
section 15.4, plan milestone M8.3).

Repository and external content is untrusted data. This detector flags
instruction-like directives that attempt to override system instructions,
policy, or tool permissions ("ignore previous instructions", "bypass",
role-switching, etc.). A positive finding requires human confirmation
before any instruction found inside a document is acted on (masterplan
section 15.4).
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class PromptInjectionFinding:
    rule: str
    match: str


# Conservative patterns ordered by specificity. False positives are
# acceptable because a flagged document requires human confirmation, it is
# not automatically blocked.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("ignore_previous_instructions", re.compile(r"(?i)\bignore (?:all |the |any )?(?:previous|prior|above|earlier) instructions\b")),
    ("system_role_switch", re.compile(r"(?i)\b(?:act as|pretend to be|you are now) (?:a|an|the)? ?(?:system|developer|admin|root)\b")),
    ("bypass_policy", re.compile(r"(?i)\b(?:bypass|circumvent|override|disable) (?:the |this )?(?:policy|approval|safety|security|permission)s?\b")),
    ("disclose_system_prompt", re.compile(r"(?i)\b(reveal|print|repeat|output) (?:your|the) (?:hidden )?(?:system prompt|instructions|hidden prompt)\b")),
    ("tool_permission_change", re.compile(r"(?i)\b(?:give yourself|grant yourself|escalate) (?:tool |write |admin |sudo )?permissions\b")),
    ("prompt_leak_marker", re.compile(r"(?i)\b\[system\]|\[developer\]|<<SYS>>|ignore all constraints\b")),
]


def scan_prompt_injection(text: str) -> list[PromptInjectionFinding]:
    findings: list[PromptInjectionFinding] = []
    for rule, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(PromptInjectionFinding(rule=rule, match=match.group(0)))
    return findings


def has_prompt_injection(text: str) -> bool:
    return bool(scan_prompt_injection(text))
