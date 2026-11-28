"""External issue-management exporters (Jira, DefectDojo) and assessment notifications."""

from __future__ import annotations

import base64
import json
import urllib.request
from datetime import datetime, timezone

from noxentra.compliance import redact_secrets
from noxentra.engagement import Engagement
from noxentra.findings import Finding


def _post_json(url: str, payload: dict, headers: dict[str, str], *, timeout: int = 15) -> int:
    body = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        url,
        data=body,
        headers={"Content-Type": "application/json", **headers},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return int(getattr(resp, "status", 200))


def build_jira_issues(
    e: Engagement,
    findings: list[Finding],
    *,
    project_key: str = "SEC",
    min_severities: tuple[str, ...] = ("critical", "high"),
) -> list[dict]:
    """Build Jira REST API v3 issue payloads for high-priority engagement findings."""
    issues: list[dict] = []
    allowed = {s.lower() for s in min_severities}
    for f in findings:
        if f.severity.lower() not in allowed:
            continue
        desc = redact_secrets(
            f"Engagement: {e.name}\nTarget: {f.target}\nTool: {f.source_tool}\n"
            f"Severity: {f.severity}\nEvidence ID: {f.details.get('evidence_id', 'n/a')}"
        )
        issues.append({
            "fields": {
                "project": {"key": project_key},
                "summary": f"[Noxentra][{f.severity.upper()}] {f.name[:180]}",
                "description": desc,
                "issuetype": {"name": "Bug"},
                "labels": ["noxentra", f.kind, f.source_tool],
            }
        })
    return issues


def push_jira(
    base_url: str,
    email: str,
    api_token: str,
    issues: list[dict],
    *,
    timeout: int = 15,
) -> int:
    """Push Jira issue payloads to `<base_url>/rest/api/2/issue` and return created count."""
    token = base64.b64encode(f"{email}:{api_token}".encode()).decode("ascii")
    headers = {"Authorization": f"Basic {token}"}
    endpoint = f"{base_url.rstrip('/')}/rest/api/2/issue"
    created = 0
    for issue in issues:
        _post_json(endpoint, issue, headers, timeout=timeout)
        created += 1
    return created


def build_defectdojo_payload(e: Engagement, findings: list[Finding]) -> dict:
    """Build a DefectDojo Generic Findings Import JSON payload."""
    items = []
    for f in findings:
        sev = f.severity.capitalize()
        if sev not in ("Critical", "High", "Medium", "Low", "Info"):
            sev = "Info"
        items.append({
            "title": f.name[:200],
            "severity": sev,
            "description": redact_secrets(f"Target: {f.target} (tool={f.source_tool})"),
            "mitigation": "Review finding and apply remediation per engagement evidence.",
            "active": True,
            "verified": False,
            "endpoints": [f.target] if f.target.startswith(("http://", "https://")) else [],
        })
    return {
        "engagement_name": e.name,
        "scan_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "findings": items,
    }


def push_defectdojo(
    base_url: str,
    api_key: str,
    engagement_id: int,
    e: Engagement,
    findings: list[Finding],
    *,
    timeout: int = 15,
) -> int:
    """Push normalized findings to DefectDojo's `/api/v2/import-scan/` endpoint."""
    payload = build_defectdojo_payload(e, findings)
    payload["engagement"] = engagement_id
    endpoint = f"{base_url.rstrip('/')}/api/v2/import-scan/"
    return _post_json(endpoint, payload, {"Authorization": f"Token {api_key}"}, timeout=timeout)


def notify_webhook(
    webhook_url: str,
    *,
    event: str,
    engagement_name: str,
    summary: str,
    status: str = "completed",
    timeout: int = 10,
) -> int:
    """Send an assessment lifecycle notification (completed/failed/cancelled/blocked) to a webhook."""
    payload = {
        "source": "noxentra",
        "event": event,
        "status": status,
        "engagement": engagement_name,
        "summary": redact_secrets(summary),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    return _post_json(webhook_url, payload, {}, timeout=timeout)
