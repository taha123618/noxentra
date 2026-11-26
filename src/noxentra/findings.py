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


PARSERS = {
    "subfinder": parse_subfinder,
    "httpx": parse_httpx,
    "nuclei": parse_nuclei,
    "nmap": parse_nmap,
    "gobuster": parse_gobuster,
}


def save_findings(path: Path, findings: list[Finding]) -> None:
    from noxentra.storage import write_json
    write_json(path, [asdict(f) for f in findings], indent=2)


def load_findings(path: Path) -> list[Finding]:
    if not path.exists():
        return []
    return [Finding(**d) for d in json.loads(path.read_text(encoding="utf-8"))]
