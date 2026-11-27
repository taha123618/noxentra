import json
from pathlib import Path

from noxentra.findings import (
    Finding,
    diff_findings,
    load_findings,
    merge_findings,
    parse_dnsx,
    parse_feroxbuster,
    parse_ffuf,
    parse_gau,
    parse_gobuster,
    parse_grype,
    parse_httpx,
    parse_katana,
    parse_nmap,
    parse_nuclei,
    parse_subfinder,
    parse_tlsx,
    parse_trivy,
    parse_whatweb,
    save_findings,
)

TS = "2026-07-05T00:00:00+00:00"

def test_parse_subfinder():
    raw = "a.example.com\nb.example.com\n\n"
    fs, forward = parse_subfinder(raw, TS)
    assert forward == ["a.example.com", "b.example.com"]
    assert [f.kind for f in fs] == ["subdomain", "subdomain"]
    assert fs[0].target == "a.example.com"
    assert fs[0].source_tool == "subfinder"
    assert fs[0].severity == "info"

def test_parse_httpx_forwards_bare_urls():
    raw = (
        json.dumps({"url": "https://a.example.com", "status_code": 200,
                    "title": "Home", "tech": ["nginx"]}) + "\n"
        + "not-json-skip-me\n"
        + json.dumps({"url": "https://b.example.com", "status_code": 403}) + "\n"
    )
    fs, forward = parse_httpx(raw, TS)
    assert forward == ["https://a.example.com", "https://b.example.com"]
    assert fs[0].kind == "service"
    assert fs[0].details["status_code"] == 200
    assert fs[0].details["tech"] == ["nginx"]

def test_parse_nuclei():
    raw = json.dumps({
        "template-id": "exposed-git",
        "info": {"name": "Exposed .git", "severity": "high"},
        "matched-at": "https://a.example.com/.git/",
        "type": "http",
    }) + "\n"
    fs, forward = parse_nuclei(raw, TS)
    assert forward == []
    assert fs[0].kind == "vulnerability"
    assert fs[0].severity == "high"
    assert fs[0].name == "Exposed .git"
    assert fs[0].target == "https://a.example.com/.git/"
    assert fs[0].details["template_id"] == "exposed-git"

def test_save_and_load_roundtrip(tmp_path: Path):
    fs = [Finding("subdomain", "a.example.com", "a.example.com", "info",
                  "subfinder", {}, "a.example.com", TS)]
    p = tmp_path / "findings.json"
    save_findings(p, fs)
    loaded = load_findings(p)
    assert loaded == fs


def test_parse_nmap():
    raw = (
        "# Nmap 7.94 scan\n"
        "Host: 10.0.0.1 (web.example.com)\tPorts: 22/open/tcp//ssh//OpenSSH 8.9/, "
        "443/open/tcp//https//nginx/\tIgnored State: closed\n"
    )
    fs, forward = parse_nmap(raw, TS)
    assert len(fs) == 2
    assert fs[0].kind == "service" and fs[0].source_tool == "nmap"
    assert fs[0].target == "web.example.com"
    assert "22/tcp" in fs[0].name
    assert forward == ["https://web.example.com"]


def test_parse_gobuster():
    raw = (
        "/admin                (Status: 301) [Size: 178] [--> /admin/]\n"
        "https://example.com/api (Status: 200) [Size: 42]\n"
    )
    fs, forward = parse_gobuster(raw, TS)
    assert len(fs) == 2
    assert fs[0].source_tool == "gobuster"
    assert fs[0].details["status_code"] == 301
    assert forward == ["https://example.com/api"]


def test_merge_findings_deduplicates_preserving_newer():
    old = [
        Finding("subdomain", "a.example.com", "a.example.com", "info", "subfinder", {}, "a", "t1"),
        Finding("service", "https://a.example.com", "Old", "info", "httpx", {"status_code": 200}, "x", "t1"),
    ]
    new = [
        Finding("subdomain", "a.example.com", "a.example.com", "info", "subfinder", {}, "a", "t2"),
        Finding("subdomain", "b.example.com", "b.example.com", "info", "subfinder", {}, "b", "t2"),
    ]
    merged = merge_findings(old, new)
    assert len(merged) == 3
    by_target = {f.target: f for f in merged}
    assert by_target["a.example.com"].timestamp == "t2"
    assert "b.example.com" in by_target

    merged2, new_count = diff_findings(old, new)
    assert len(merged2) == 3
    assert new_count == 1


def test_parse_ffuf():
    raw = json.dumps({
        "results": [
            {"url": "https://example.com/admin", "status": 301, "length": 162, "input": {"FUZZ": "admin"}}
        ]
    })
    fs, forward = parse_ffuf(raw, TS)
    assert len(fs) == 1
    assert fs[0].source_tool == "ffuf"
    assert fs[0].details["status_code"] == 301
    assert forward == ["https://example.com/admin"]


def test_parse_feroxbuster():
    raw = (
        json.dumps({"type": "configuration", "url": "https://example.com"}) + "\n"
        + json.dumps({"type": "response", "url": "https://example.com/api", "status": 200, "content_length": 44}) + "\n"
    )
    fs, forward = parse_feroxbuster(raw, TS)
    assert len(fs) == 1
    assert fs[0].source_tool == "feroxbuster"
    assert forward == ["https://example.com/api"]


def test_parse_dnsx():
    raw = json.dumps({"host": "api.example.com", "a": ["93.184.216.34"]}) + "\n"
    fs, forward = parse_dnsx(raw, TS)
    assert len(fs) == 1
    assert fs[0].kind == "subdomain"
    assert fs[0].details["a"] == ["93.184.216.34"]
    assert forward == ["api.example.com"]


def test_parse_whatweb():
    raw = json.dumps([{"target": "https://example.com", "http_status": 200, "plugins": {"nginx": {}, "HTTPServer": {}}}])
    fs, forward = parse_whatweb(raw, TS)
    assert len(fs) == 1
    assert fs[0].source_tool == "whatweb"
    assert "nginx" in fs[0].details["tech"]
    assert forward == ["https://example.com"]


def test_parse_gau():
    raw = "https://example.com/a\nhttps://example.com/a\nnot-a-url\nhttp://example.com/b\n"
    fs, forward = parse_gau(raw, TS)
    assert len(fs) == 2
    assert fs[0].source_tool == "gau"
    assert forward == ["https://example.com/a", "http://example.com/b"]


def test_parse_tlsx():
    raw = json.dumps({
        "host": "example.com",
        "port": 443,
        "subject_cn": "example.com",
        "subject_an": ["*.example.com", "api.example.com"],
        "tls_version": "tls13",
    }) + "\n"
    fs, forward = parse_tlsx(raw, TS)
    assert len(fs) == 1
    assert fs[0].source_tool == "tlsx"
    assert "example.com:443" in fs[0].name
    assert forward == ["example.com", "api.example.com"]


def test_parse_katana():
    raw = (
        json.dumps({"request": {"method": "POST", "endpoint": "https://example.com/api/login"}}) + "\n"
        + "https://example.com/robots.txt\n"
    )
    fs, forward = parse_katana(raw, TS)
    assert len(fs) == 2
    assert fs[0].name == "POST https://example.com/api/login"
    assert forward == ["https://example.com/api/login", "https://example.com/robots.txt"]


def test_parse_trivy():
    raw = json.dumps({
        "ArtifactName": "alpine:3.19",
        "Results": [{
            "Target": "alpine:3.19 (alpine 3.19.1)",
            "Vulnerabilities": [{
                "VulnerabilityID": "CVE-2024-0001",
                "PkgName": "openssl",
                "Severity": "HIGH",
                "Title": "OpenSSL issue",
            }],
        }],
    })
    fs, targets = parse_trivy(raw, TS)
    assert len(fs) == 1
    assert fs[0].severity == "high"
    assert fs[0].source_tool == "trivy"
    assert fs[0].details["template_id"] == "CVE-2024-0001"
    assert targets == ["alpine:3.19 (alpine 3.19.1)"]


def test_parse_grype():
    raw = json.dumps({
        "source": {"target": {"userInput": "dir:."}},
        "matches": [{
            "vulnerability": {"id": "GHSA-1234", "severity": "Critical"},
            "artifact": {"name": "urllib3", "version": "1.26.0"},
        }],
    })
    fs, targets = parse_grype(raw, TS)
    assert len(fs) == 1
    assert fs[0].severity == "critical"
    assert fs[0].source_tool == "grype"
    assert targets == ["dir:."]
