"""Secrets redaction and security compliance mapping (OWASP, CWE, MITRE ATT&CK, NIST)."""

from __future__ import annotations

import re

from noxentra.findings import Finding
from noxentra.vuln_intel import extract_identifiers

_SECRET_PATTERNS: list[tuple[re.Pattern[str], str]] = [
    (re.compile(r"AKIA[0-9A-Z]{16}"), "[REDACTED:AWS_KEY]"),
    (re.compile(r"gh[pousr]_[A-Za-z0-9_]{20,}"), "[REDACTED:GITHUB_TOKEN]"),
    (re.compile(r"sk-[A-Za-z0-9]{20,}"), "[REDACTED:API_KEY]"),
    (re.compile(r"(?i)(bearer\s+)[A-Za-z0-9\-._~+/]+=*"), r"\1[REDACTED:BEARER]"),
    (re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----[\s\S]*?-----END [A-Z ]*PRIVATE KEY-----"), "[REDACTED:PRIVATE_KEY]"),
]


def redact_secrets(text: str) -> str:
    """Redact common credentials, tokens, and private keys before logging or AI requests."""
    out = text
    for pat, repl in _SECRET_PATTERNS:
        out = pat.sub(repl, out)
    return out


_KIND_CONTROLS: dict[str, dict[str, list[str]]] = {
    "secret": {
        "owasp": ["A07:2021-Identification and Authentication Failures"],
        "mitre": ["T1552-Unsecured Credentials"],
        "nist": ["IA-5", "SC-12"],
    },
    "iam-risk": {
        "owasp": ["A01:2021-Broken Access Control"],
        "mitre": ["T1078-Valid Accounts", "T1098-Account Manipulation"],
        "nist": ["AC-2", "AC-6"],
    },
    "misconfiguration": {
        "owasp": ["A05:2021-Security Misconfiguration"],
        "mitre": ["T1574-Hijack Execution Flow"],
        "nist": ["CM-6", "CM-7"],
    },
    "vulnerability": {
        "owasp": ["A06:2021-Vulnerable and Outdated Components"],
        "mitre": ["T1190-Exploit Public-Facing Application"],
        "nist": ["SI-2", "RA-5"],
    },
    "subdomain": {
        "owasp": ["A05:2021-Security Misconfiguration"],
        "mitre": ["T1590-Gather Victim Network Information"],
        "nist": ["CA-9"],
    },
    "service": {
        "owasp": ["A05:2021-Security Misconfiguration"],
        "mitre": ["T1046-Network Service Discovery"],
        "nist": ["CM-8"],
    },
}


def map_finding_compliance(finding: Finding) -> dict[str, list[str]]:
    """Map a Finding to OWASP Top 10, CWE, MITRE ATT&CK, and NIST 800-53 controls."""
    _, cwes = extract_identifiers(finding)
    base = _KIND_CONTROLS.get(finding.kind, _KIND_CONTROLS["vulnerability"])
    return {
        "owasp": list(base["owasp"]),
        "cwe": cwes,
        "mitre": list(base["mitre"]),
        "nist": list(base["nist"]),
    }
