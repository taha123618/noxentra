import json
from pathlib import Path

from noxentra.findings import (
    Finding,
    load_findings,
    parse_gobuster,
    parse_httpx,
    parse_nmap,
    parse_nuclei,
    parse_subfinder,
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
