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


def parse_gau(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `gau` / `waybackurls` line-delimited URLs into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    seen: set[str] = set()
    for ln in raw.splitlines():
        url = ln.strip()
        if not url or not url.startswith(("http://", "https://")) or url in seen:
            continue
        seen.add(url)
        findings.append(Finding("service", url, url, "info", "gau", {}, url, ts))
        urls.append(url)
    return findings, urls


def parse_tlsx(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `tlsx -json` JSONL certificate metadata into service Findings and SANs."""
    findings: list[Finding] = []
    hosts: list[str] = []
    seen_hosts: set[str] = set()
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
        host = obj.get("host") or obj.get("ip") or ""
        if not isinstance(host, str) or not host:
            continue
        cn = obj.get("subject_cn") or ""
        sans = [s for s in (obj.get("subject_an") or []) if isinstance(s, str)]
        port = obj.get("port") or 443
        label = f"{host}:{port} ({cn})" if cn else f"{host}:{port}"
        details = {"port": port, "subject_cn": cn, "subject_an": sans, "tls_version": obj.get("tls_version")}
        findings.append(Finding("service", host, label, "info", "tlsx", details, ln, ts))
        for candidate in [host, *sans]:
            clean = candidate.lstrip("*.")
            if clean and clean not in seen_hosts:
                seen_hosts.add(clean)
                hosts.append(clean)
    return findings, hosts


def parse_katana(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `katana` JSONL (`-jsonl`) or plain crawled URLs into service Findings."""
    findings: list[Finding] = []
    urls: list[str] = []
    for ln in raw.splitlines():
        ln = ln.strip()
        if not ln:
            continue
        url = ""
        method = "GET"
        try:
            obj = json.loads(ln)
            if isinstance(obj, dict):
                req = obj.get("request") if isinstance(obj.get("request"), dict) else {}
                url = req.get("endpoint") or obj.get("endpoint") or obj.get("url") or ""
                method = req.get("method") or "GET"
        except json.JSONDecodeError:
            if ln.startswith(("http://", "https://")):
                url = ln
        if not isinstance(url, str) or not url:
            continue
        label = f"{method} {url}" if method != "GET" else url
        findings.append(Finding("service", url, label, "info", "katana", {"method": method}, ln, ts))
        urls.append(url)
    return findings, urls


def parse_trivy(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `trivy ... -f json` output into vulnerability Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    text = raw.strip()
    if not text:
        return findings, targets
    try:
        top = json.loads(text)
    except json.JSONDecodeError:
        return findings, targets
    if not isinstance(top, dict):
        return findings, targets

    artifact = str(top.get("ArtifactName") or "")
    for res in top.get("Results") or []:
        if not isinstance(res, dict):
            continue
        res_target = str(res.get("Target") or artifact or "unknown")
        for v in res.get("Vulnerabilities") or []:
            if not isinstance(v, dict):
                continue
            vid = str(v.get("VulnerabilityID") or "")
            pkg = str(v.get("PkgName") or "")
            sev = str(v.get("Severity") or "unknown").lower()
            title = str(v.get("Title") or vid or pkg)
            name = f"{vid}: {pkg} ({title})" if pkg else title
            details = {
                "template_id": vid,
                "pkg": pkg,
                "installed_version": v.get("InstalledVersion"),
                "fixed_version": v.get("FixedVersion"),
            }
            findings.append(Finding("vulnerability", res_target, name, sev, "trivy", details, json.dumps(v), ts))
            if res_target not in targets:
                targets.append(res_target)
    return findings, targets


def parse_grype(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `grype ... -o json` output into vulnerability Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    text = raw.strip()
    if not text:
        return findings, targets
    try:
        top = json.loads(text)
    except json.JSONDecodeError:
        return findings, targets
    if not isinstance(top, dict):
        return findings, targets

    source = top.get("source") if isinstance(top.get("source"), dict) else {}
    target_obj = source.get("target")
    default_target = str(target_obj.get("userInput") if isinstance(target_obj, dict) else (target_obj or "artifact"))
    for match in top.get("matches") or []:
        if not isinstance(match, dict):
            continue
        vuln = match.get("vulnerability") if isinstance(match.get("vulnerability"), dict) else {}
        art = match.get("artifact") if isinstance(match.get("artifact"), dict) else {}
        vid = str(vuln.get("id") or "")
        pkg = str(art.get("name") or "")
        sev = str(vuln.get("severity") or "unknown").lower()
        name = f"{vid}: {pkg}" if pkg and vid else (vid or pkg or "vulnerability")
        details = {"template_id": vid, "pkg": pkg, "version": art.get("version")}
        findings.append(Finding("vulnerability", default_target, name, sev, "grype", details, json.dumps(match), ts))
        if default_target not in targets:
            targets.append(default_target)
    return findings, targets


def _load_json_dict(raw: str) -> dict | None:
    """Parse `raw` as a JSON object, returning None on empty/invalid/non-dict input."""
    text = raw.strip()
    if not text:
        return None
    try:
        top = json.loads(text)
    except json.JSONDecodeError:
        return None
    return top if isinstance(top, dict) else None


def parse_terrascan(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `terrascan scan -o json` output into IaC misconfiguration Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    top = _load_json_dict(raw)
    if not top:
        return findings, targets

    results = top.get("results") if isinstance(top.get("results"), dict) else {}
    for v in results.get("violations") or []:
        if not isinstance(v, dict):
            continue
        rule_id = str(v.get("rule_id") or "")
        rule_name = str(v.get("rule_name") or rule_id or "terrascan-violation")
        sev = str(v.get("severity") or "medium").lower()
        target = str(v.get("file") or v.get("resource_name") or "iac")
        line = v.get("line")
        loc = f"{target}:{line}" if line else target
        name = f"{rule_id}: {rule_name}" if rule_id else rule_name
        details = {
            "rule_id": rule_id,
            "category": v.get("category"),
            "resource_name": v.get("resource_name"),
            "resource_type": v.get("resource_type"),
            "description": v.get("description"),
        }
        findings.append(Finding("misconfiguration", loc, name, sev, "terrascan", details, json.dumps(v), ts))
        if target not in targets:
            targets.append(target)
    return findings, targets


def parse_kube_hunter(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `kube-hunter --report json` output into Kubernetes Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    top = _load_json_dict(raw)
    if not top:
        return findings, targets

    for v in top.get("vulnerabilities") or []:
        if not isinstance(v, dict):
            continue
        vuln = str(v.get("vulnerability") or v.get("vid") or "kube-hunter-finding")
        sev = str(v.get("severity") or "medium").lower()
        loc = str(v.get("location") or "cluster")
        details = {
            "vid": v.get("vid"),
            "avd_reference": v.get("avd_reference"),
            "category": v.get("category"),
            "description": v.get("description"),
        }
        findings.append(Finding("vulnerability", loc, vuln, sev, "kube-hunter", details, json.dumps(v), ts))
        if loc not in targets:
            targets.append(loc)
    return findings, targets


def parse_cloudsplaining(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `cloudsplaining scan` JSON report into IAM Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    top = _load_json_dict(raw)
    if not top:
        return findings, targets

    risk_map = (
        ("PrivilegeEscalation", "high"),
        ("CredentialsExposure", "high"),
        ("DataExfiltration", "high"),
        ("ResourceExposure", "medium"),
        ("InfrastructureModification", "low"),
    )
    for section in ("roles", "users", "groups", "inline_policies", "customer_managed_policies", "aws_managed_policies"):
        bucket = top.get(section)
        if not isinstance(bucket, dict):
            continue
        for principal, data in bucket.items():
            if not isinstance(data, dict):
                continue
            target = str(data.get("arn") or data.get("name") or principal)
            for risk_key, sev in risk_map:
                items = data.get(risk_key) or []
                if not items:
                    continue
                name = f"{risk_key} ({len(items)})"
                details = {"section": section, "risk": risk_key, "items": items}
                findings.append(Finding("iam-risk", target, name, sev, "cloudsplaining", details, json.dumps({risk_key: items}), ts))
                if target not in targets:
                    targets.append(target)
    return findings, targets


def parse_kube_linter(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `kube-linter lint --format json` output into misconfiguration Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    top = _load_json_dict(raw)
    if not top:
        return findings, targets

    for rep in top.get("Reports") or []:
        if not isinstance(rep, dict):
            continue
        check = str(rep.get("Check") or "kube-linter-check")
        diag = rep.get("Diagnostic") if isinstance(rep.get("Diagnostic"), dict) else {}
        obj = rep.get("Object") if isinstance(rep.get("Object"), dict) else {}
        meta = obj.get("Metadata") if isinstance(obj.get("Metadata"), dict) else {}
        k8s = obj.get("K8sObject") if isinstance(obj.get("K8sObject"), dict) else {}
        fpath = str(meta.get("FilePath") or k8s.get("Name") or "k8s")
        kname = str(k8s.get("Name") or "")
        name = f"{check} ({kname})" if kname else check
        details = {
            "check": check,
            "message": diag.get("Message"),
            "remediation": rep.get("Remediation"),
            "object": kname,
        }
        findings.append(Finding("misconfiguration", fpath, name, "medium", "kube-linter", details, json.dumps(rep), ts))
        if fpath not in targets:
            targets.append(fpath)
    return findings, targets


def parse_gitleaks(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `gitleaks detect --report-format json` array into secret Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    text = raw.strip()
    if not text:
        return findings, targets
    try:
        items = json.loads(text)
    except json.JSONDecodeError:
        return findings, targets
    if not isinstance(items, list):
        return findings, targets

    for item in items:
        if not isinstance(item, dict):
            continue
        rule = str(item.get("RuleID") or item.get("Description") or "leaked-secret")
        fpath = str(item.get("File") or "repo")
        line = item.get("StartLine")
        loc = f"{fpath}:{line}" if line else fpath
        details = {
            "rule_id": item.get("RuleID"),
            "description": item.get("Description"),
            "commit": item.get("Commit"),
        }
        findings.append(Finding("secret", loc, rule, "high", "gitleaks", details, json.dumps(item), ts))
        if fpath not in targets:
            targets.append(fpath)
    return findings, targets


def parse_semgrep(raw: str, ts: str) -> tuple[list[Finding], list[str]]:
    """Parse `semgrep scan --json` output into vulnerability Findings."""
    findings: list[Finding] = []
    targets: list[str] = []
    top = _load_json_dict(raw)
    if not top:
        return findings, targets

    sev_map = {"ERROR": "high", "WARNING": "medium", "INFO": "info"}
    for res in top.get("results") or []:
        if not isinstance(res, dict):
            continue
        check_id = str(res.get("check_id") or "semgrep-rule")
        fpath = str(res.get("path") or "src")
        start = res.get("start") if isinstance(res.get("start"), dict) else {}
        line = start.get("line")
        loc = f"{fpath}:{line}" if line else fpath
        extra = res.get("extra") if isinstance(res.get("extra"), dict) else {}
        sev = sev_map.get(str(extra.get("severity") or "").upper(), "medium")
        details = {"check_id": check_id, "message": extra.get("message")}
        findings.append(Finding("vulnerability", loc, check_id, sev, "semgrep", details, json.dumps(res), ts))
        if fpath not in targets:
            targets.append(fpath)
    return findings, targets


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
    "gau": parse_gau,
    "tlsx": parse_tlsx,
    "katana": parse_katana,
    "trivy": parse_trivy,
    "grype": parse_grype,
    "terrascan": parse_terrascan,
    "kube-hunter": parse_kube_hunter,
    "cloudsplaining": parse_cloudsplaining,
    "kube-linter": parse_kube_linter,
    "gitleaks": parse_gitleaks,
    "semgrep": parse_semgrep,
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
