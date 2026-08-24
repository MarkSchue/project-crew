"""Secret scanner for staged content (masterplan section 14.4 "scan staged
content for secrets", plan milestone M4.2).

A conservative, regex-based scanner. It is not a substitute for a
dedicated secret-scanning product (Bandit/gitleaks integration is a
follow-up), but it catches the most common accidental patterns and, more
importantly, gives the scoped-write tool a deterministic rejection path
and a logged security event.
"""

from __future__ import annotations

import re
from dataclasses import dataclass


@dataclass(frozen=True)
class SecretFinding:
    rule: str
    match: str


# Ordered by specificity. Patterns are intentionally conservative: false
# positives here are acceptable because a flagged write is rejected and
# the human/operator can inspect the finding.
_PATTERNS: list[tuple[str, re.Pattern]] = [
    ("aws_access_key_id", re.compile(r"\bAKIA[0-9A-Z]{16}\b")),
    ("private_key", re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")),
    ("slack_token", re.compile(r"\bxox[baprs]-[0-9A-Za-z-]{10,}\b")),
    ("github_token", re.compile(r"\bgh[pousr]_[0-9A-Za-z]{30,}\b")),
    ("generic_password_assignment", re.compile(r"(?i)\b(password|passwd|pwd)\s*[:=]\s*[\"'][^\"']{4,}[\"']")),
]


def scan_text(text: str) -> list[SecretFinding]:
    findings: list[SecretFinding] = []
    for rule, pattern in _PATTERNS:
        for match in pattern.finditer(text):
            findings.append(SecretFinding(rule=rule, match=match.group(0)))
    return findings


def scan_bytes(content: bytes) -> list[SecretFinding]:
    return scan_text(content.decode("utf-8", errors="ignore"))


def has_secrets(content: bytes | str) -> bool:
    if isinstance(content, bytes):
        return bool(scan_bytes(content))
    return bool(scan_text(content))
