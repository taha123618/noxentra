"""Vulnerability Intelligence & Risk Enrichment (CVE, CWE, KEV/EPSS, risk scoring)."""

from __future__ import annotations

import re
from datetime import datetime, timezone

from noxentra.findings import Finding

_CVE_RE = re.compile(r"\bCVE-\d{4}-\d{4,7}\b", re.IGNORECASE)
_CWE_RE = re.compile(r"\bCWE-(\d{1,5})\b", re.IGNORECASE)

_SEVERITY_BASE = {
    "critical": 9.0,
    "high": 7.5,
    "medium": 5.0,
    "low": 2.5,
    "info": 1.0,
    "unknown": 3.0,
}

# Built-in CWE catalog subset for deterministic offline enrichment
CWE_CATALOG: dict[str, dict[str, str]] = {
    "CWE-79": {"name": "Cross-site Scripting (XSS)", "remediation": "Context-aware output encoding and strict CSP."},
    "CWE-89": {"name": "SQL Injection", "remediation": "Use parameterized queries / prepared statements."},
    "CWE-22": {"name": "Path Traversal", "remediation": "Canonicalize paths and enforce allowlisted base directories."},
    "CWE-78": {"name": "OS Command Injection", "remediation": "Use list-form subprocess APIs without shell=True."},
    "CWE-287": {"name": "Improper Authentication", "remediation": "Enforce strong authentication and token verification."},
    "CWE-347": {"name": "Improper Verification of Cryptographic Signature", "remediation": "Verify JWT/token signatures against explicit allowed algorithms."},
    "CWE-798": {"name": "Use of Hard-coded Credentials", "remediation": "Rotate exposed secrets and load credentials from a secret manager."},
    "CWE-918": {"name": "Server-Side Request Forgery (SSRF)", "remediation": "Validate outbound URLs against an allowlist and block metadata IPs."},
}


def extract_identifiers(finding: Finding) -> tuple[list[str], list[str]]:
    """Extract sorted unique CVE and CWE identifiers from a Finding."""
    haystack = " ".join([
        finding.name,
        finding.raw,
        str(finding.details),
    ])
    cves = sorted({m.upper() for m in _CVE_RE.findall(haystack)})
    cwes = sorted({f"CWE-{m}" for m in _CWE_RE.findall(haystack)})
    return cves, cwes


def compute_risk_score(
    finding: Finding,
    *,
    kev: bool = False,
    epss: float | None = None,
    internet_exposed: bool = True,
) -> float:
    """Compute a 0.0-10.0 prioritized risk score combining severity, KEV, EPSS, and exposure."""
    score = _SEVERITY_BASE.get(finding.severity.lower(), 3.0)
    if kev:
        score += 1.5
    if epss is not None and epss >= 0.5:
        score += 1.0
    elif epss is not None and epss >= 0.1:
        score += 0.5
    if not internet_exposed:
        score -= 0.5
    return round(max(0.0, min(10.0, score)), 2)


def enrich_finding(
    finding: Finding,
    *,
    kev_set: set[str] | frozenset[str] = frozenset(),
    epss_map: dict[str, float] | None = None,
    source: str = "noxentra-offline-intel",
    enriched_at: str | None = None,
) -> Finding:
    """Attach CVE/CWE, KEV/EPSS, remediation, and risk score without mutating raw evidence."""
    ts = enriched_at or datetime.now(timezone.utc).isoformat()
    cves, cwes = extract_identifiers(finding)
    in_kev = any(cve in kev_set for cve in cves)
    epss_vals = [epss_map[c] for c in cves if epss_map and c in epss_map]
    max_epss = max(epss_vals) if epss_vals else None

    cwe_info = [
        {"id": cwe, **CWE_CATALOG[cwe]}
        for cwe in cwes
        if cwe in CWE_CATALOG
    ]
    risk_score = compute_risk_score(finding, kev=in_kev, epss=max_epss)

    details = dict(finding.details)
    details["intel"] = {
        "cves": cves,
        "cwes": cwes,
        "cwe_details": cwe_info,
        "kev": in_kev,
        "epss": max_epss,
        "risk_score": risk_score,
        "source": source,
        "enriched_at": ts,
    }
    return Finding(
        kind=finding.kind,
        target=finding.target,
        name=finding.name,
        severity=finding.severity,
        source_tool=finding.source_tool,
        details=details,
        raw=finding.raw,
        timestamp=finding.timestamp,
    )


def enrich_findings(
    findings: list[Finding],
    *,
    kev_set: set[str] | frozenset[str] = frozenset(),
    epss_map: dict[str, float] | None = None,
) -> list[Finding]:
    """Enrich all findings and sort highest risk score first."""
    ts = datetime.now(timezone.utc).isoformat()
    enriched = [
        enrich_finding(f, kev_set=kev_set, epss_map=epss_map, enriched_at=ts)
        for f in findings
    ]
    return sorted(
        enriched,
        key=lambda f: float(f.details.get("intel", {}).get("risk_score", 0.0)),
        reverse=True,
    )
