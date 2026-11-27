"""Normalized findings schema + per-tool parsers. Stdlib only."""
import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path


@dataclass
class Finding:
    kind: str          # subdomain | service | vulnerability
    target: str
    name: str
    severity: str      # info | low | medium | high | critical | unknown
    source_tool: str
    details: dict
    raw: str
    timestamp: str


def parse_subfinder(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    hosts = [ln.strip() for ln in raw.splitlines() if ln.strip()]
    findings = [Finding("subdomain", h, h, "info", "subfinder", {}, h, ts) for h in hosts]
    return findings, hosts


def parse_httpx(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    urls: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue  # skip malformed line, keep going
        if not isinstance(obj, dict):          # valid JSON but not an object → skip
            continue
        url = obj.get("url") or obj.get("input") or ""
        if not isinstance(url, str) or not url:
            continue
        title = obj.get("title")
        title = title if isinstance(title, str) and title else url
        details = {
            "status_code": obj.get("status_code"),
            "title": obj.get("title"),
            "tech": obj.get("tech"),
            "webserver": obj.get("webserver"),
        }
        findings.append(Finding("service", url, title, "info", "httpx", details, ln, ts))
        urls.append(url)
    return findings, urls


def parse_nuclei(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    findings: list[Finding] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):          # valid JSON but not an object → skip
            continue
        info = obj.get("info")
        if not isinstance(info, dict):
            info = {}
        target = obj.get("matched-at") or obj.get("host") or ""
        if not isinstance(target, str):
            target = ""
        tid = obj.get("template-id", "")
        tid = tid if isinstance(tid, str) else ""
        name = info.get("name") or tid
        name = name if isinstance(name, str) and name else tid
        sev = info.get("severity")
        sev = sev if isinstance(sev, str) and sev else "unknown"
        details = {"template_id": tid, "matched_at": obj.get("matched-at"),
                   "type": obj.get("type")}
        findings.append(Finding("vulnerability", target, name, sev, "nuclei",
                                details, ln, ts))
    return findings, []


_GOBUSTER_RE = re.compile(
    r"^(?P<path>\S+)\s+\(Status:\s*(?P<status>\d+)\)(?:\s+\[Size:\s*(?P<size>\d+)\])?"
)


def parse_nmap(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse grepable nmap output (`nmap -oG -`) into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln.startswith("Host:") or "Ports:" not in ln:
            continue
        host_part, ports_part = ln.split("Ports:", 1)
        m_host = re.match(r"Host:\s+(\S+)(?:\s+\(([^)]*)\))?", host_part)
        if not m_host:
            continue
        ip, rdns = m_host.group(1), (m_host.group(2) or "").strip()
        host = rdns or ip
        for entry in ports_part.split(","):
            fields = [f.strip() for f in entry.strip().split("/")]
            if len(fields) < 5 or fields[1] != "open":
                continue
            port, _state, proto, _owner, service = fields[:5]
            version = fields[6] if len(fields) > 6 else ""
            svc_label = f"{service} {version}".strip() if version else (service or "unknown")
            name = f"{port}/{proto} ({svc_label})"
            details = {"ip": ip, "port": port, "proto": proto, "service": service, "version": version}
            findings.append(Finding("service", host, name, "info", "nmap", details, ln, ts))
            if service in ("http", "https", "http-alt", "ssl/http") or port in ("80", "443", "8080", "8443"):
                scheme = "https" if ("https" in service or "ssl" in service or port in ("443", "8443")) else "http"
                u = f"{scheme}://{host}" if port in ("80", "443") else f"{scheme}://{host}:{port}"
                if u not in urls:
                    urls.append(u)
    return findings, urls


def parse_gobuster(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse gobuster stdout lines into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        m = _GOBUSTER_RE.match(ln)
        if not m:
            continue
        path = m.group("path")
        status = int(m.group("status"))
        size = int(m.group("size")) if m.group("size") else None
        details = {"status_code": status, "size": size}
        findings.append(Finding("service", path, f"{path} (HTTP {status})", "info", "gobuster", details, ln, ts))
        if path.startswith(("http://", "https://")):
            urls.append(path)
    return findings, urls


def parse_ffuf(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse ffuf JSON (`-of json`) or JSONL lines into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    text = raw.strip()
    if not text:
        return findings, urls

    records: list[tuple[dict, str]] = []
    try:
        top = json.loads(text)
    except json.JSONDecodeError:
        top = None
    if isinstance(top, dict) and isinstance(top.get("results"), list):
        for item in top["results"]:
            if isinstance(item, dict):
                records.append((item, json.dumps(item)))
    else:
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append((obj, ln))

    for obj, raw_ln in records:
        url = obj.get("url") or ""
        if not isinstance(url, str) or not url:
            continue
        status = obj.get("status")
        length = obj.get("length")
        label = f"{url} (HTTP {status})" if status is not None else url
        details = {"status_code": status, "length": length, "input": obj.get("input")}
        findings.append(Finding("service", url, label, "info", "ffuf", details, raw_ln, ts))
        urls.append(url)
    return findings, urls


def parse_feroxbuster(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse feroxbuster JSONL (`--json`) lines into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            continue
        if not isinstance(obj, dict):
            continue
        if obj.get("type") not in (None, "response"):
            continue
        url = obj.get("url") or ""
        if not isinstance(url, str) or not url:
            continue
        status = obj.get("status")
        length = obj.get("content_length")
        label = f"{url} (HTTP {status})" if status is not None else url
        details = {"status_code": status, "content_length": length}
        findings.append(Finding("service", url, label, "info", "feroxbuster", details, ln, ts))
        urls.append(url)
    return findings, urls


def parse_dnsx(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse dnsx JSONL (`-json`) or plain hostname output into subdomain Findings."""
    findings: list[Finding] = []
    hosts: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        try:
            obj = json.loads(ln)
        except json.JSONDecodeError:
            findings.append(Finding("subdomain", ln, ln, "info", "dnsx", {}, ln, ts))
            hosts.append(ln)
            continue
        if not isinstance(obj, dict):
            continue
        host = obj.get("host") or ""
        if not isinstance(host, str) or not host:
            continue
        details = {
            k: obj[k]
            for k in ("a", "aaaa", "cname", "mx", "ns", "txt")
            if obj.get(k)
        }
        findings.append(Finding("subdomain", host, host, "info", "dnsx", details, ln, ts))
        hosts.append(host)
    return findings, hosts


def parse_whatweb(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse WhatWeb JSON (`--log-json=-`) array or JSONL into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    text = raw.strip()
    if not text:
        return findings, urls

    records: list[tuple[dict, str]] = []
    try:
        parsed = json.loads(text)
    except json.JSONDecodeError:
        parsed = None
    if isinstance(parsed, list):
        for item in parsed:
            if isinstance(item, dict):
                records.append((item, json.dumps(item)))
    elif isinstance(parsed, dict):
        records.append((parsed, text))
    else:
        for ln in text.splitlines():
            ln = ln.strip()
            if not ln:
                continue
            try:
                obj = json.loads(ln)
            except json.JSONDecodeError:
                continue
            if isinstance(obj, dict):
                records.append((obj, ln))

    for obj, raw_ln in records:
        target = obj.get("target") or ""
        if not isinstance(target, str) or not target:
            continue
        plugins = obj.get("plugins") if isinstance(obj.get("plugins"), dict) else {}
        tech = sorted(plugins.keys())
        status = obj.get("http_status")
        name = f"{target} [{', '.join(tech[:4])}]" if tech else target
        details = {"status_code": status, "tech": tech}
        findings.append(Finding("service", target, name, "info", "whatweb", details, raw_ln, ts))
        urls.append(target)
    return findings, urls


PARSERS = {
    "subfinder": parse_subfinder,
    "httpx": parse_httpx,
    "nuclei": parse_nuclei,
    "nmap": parse_nmap,
    "gobuster": parse_gobuster,
    "ffuf": parse_ffuf,
    "feroxbuster": parse_feroxbuster,
    "dnsx": parse_dnsx,
    "whatweb": parse_whatweb,
}


def diff_findings(existing: list[Finding], incoming: list[Finding]) -> tuple[list[Finding], int]:
    """Merge `existing` and `incoming` by `(kind, target, name, source_tool)` and return `(merged, new_count)`."""
    merged: dict[tuple[str, str, str, str], Finding] = {}
    for f in existing:
        merged[(f.kind, f.target, f.name, f.source_tool)] = f
    new_count = 0
    for f in incoming:
        key = (f.kind, f.target, f.name, f.source_tool)
        if key not in merged:
            new_count += 1
        merged[key] = f
    return list(merged.values()), new_count


def merge_findings(existing: list[Finding], incoming: list[Finding]) -> list[Finding]:
    """Combine `existing` and `incoming`, deduplicating by `(kind, target, name, source_tool)`."""
    merged, _ = diff_findings(existing, incoming)
    return merged


def save_findings(path: Path, findings: list[Finding]) -> None:
    from noxentra.storage import write_json
    write_json(path, [asdict(f) for f in findings], indent=2)


def load_findings(path: Path) -> list[Finding]:
    if not path.exists():
        return []
    return [Finding(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
