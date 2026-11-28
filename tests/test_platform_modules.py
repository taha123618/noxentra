"""Unit tests for the P0/P1/P2 platform intelligence, policy, evidence, API, CI/CD, and DFIR modules."""

from __future__ import annotations

import base64
import json
import subprocess

import pytest

from noxentra import (
    api_assess,
    assets,
    cicd,
    compliance,
    dfir,
    doctor,
    engagement,
    evidence,
    orchestrator,
    plugin_sdk,
    policy,
    vuln_intel,
)
from noxentra.findings import Finding


def _isolate_home(tmp_path, monkeypatch):
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path / "engagements")
    monkeypatch.setattr(dfir, "CASES_ROOT", tmp_path / "cases")


def test_doctor_returns_structured_checks():
    checks = doctor.run_diagnostics()
    names = {c.name for c in checks}
    assert {"python", "platform", "git", "pipeline_tools"}.issubset(names)
    assert all(c.status in ("ok", "warn", "fail") for c in checks)


def test_assets_graph_and_diff(tmp_path):
    ts = "2026-11-28T00:00:00+00:00"
    findings = [
        Finding("subdomain", "api.example.com", "api.example.com", "info", "subfinder", {"a": ["1.2.3.4"]}, "api.example.com", ts),
        Finding("service", "https://api.example.com/v1/api/users", "Users API", "info", "httpx", {"status_code": 200}, "{}", ts),
        Finding("service", "api.example.com", "443/tcp (https)", "info", "nmap", {"port": "443", "proto": "tcp", "service": "https"}, "", ts),
    ]
    node_list, edge_list = assets.build_assets_from_findings(["example.com"], findings, timestamp=ts)
    kinds = {a.kind for a in node_list}
    assert {"domain", "subdomain", "ip", "api", "port"}.issubset(kinds)
    assert "has_subdomain" in {e.relation for e in edge_list}
    assert "resolves_to" in {e.relation for e in edge_list}

    p = tmp_path / "assets.json"
    assets.save_assets(p, node_list, edge_list)
    loaded_nodes, loaded_edges = assets.load_assets(p)
    assert len(loaded_nodes) == len(node_list)
    assert len(loaded_edges) == len(edge_list)
    assert "Assets:" in assets.render_graph_text(loaded_nodes, loaded_edges)

    diff = assets.diff_assets(loaded_nodes[:-1], loaded_nodes)
    assert len(diff["added"]) == 1
    assert diff["removed"] == []


def test_policy_engine_enforces_profiles_and_scope():
    dec_block = policy.evaluate_execution("passive_recon", "nuclei", ["a.example.com"])
    assert dec_block.allowed is False
    assert "exceeds" in dec_block.reason or "disallows" in dec_block.reason

    dec_allow = policy.evaluate_execution(
        "safe_active",
        "httpx",
        ["in.example.com", "out.example.com"],
        scope_out=["out.example.com"],
    )
    assert dec_allow.allowed is True
    assert dec_allow.effective_targets == ["in.example.com"]


def test_evidence_and_orchestrator_policy_integration(tmp_path, monkeypatch):
    _isolate_home(tmp_path, monkeypatch)
    e = engagement.create("acme-pol", targets=["example.com"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: f"/usr/bin/{t}")

    def fake_run(cmd, input=None, **kwargs):
        if cmd[0] == "subfinder":
            return subprocess.CompletedProcess(cmd, 0, stdout="app.example.com\n", stderr="")
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    # passive_recon allows subfinder (low) and blocks httpx/nuclei
    found = orchestrator.run_pipeline(e, "recon", profile="passive_recon")
    assert len(found) == 1
    assert "evidence_id" in found[0].details
    assert "evidence_sha256" in found[0].details

    manifest = evidence.load_manifest(e.workspace)
    assert len(manifest) == 1
    assert evidence.verify_evidence(e.workspace, manifest[0]) is True
    assert (e.workspace / "assets.json").exists()


def test_vuln_intel_enrichment():
    f = Finding("vulnerability", "https://x.com", "SQLi CVE-2024-1234 (CWE-89)", "high", "nuclei", {}, "raw", "2026-01-01")
    enriched = vuln_intel.enrich_findings([f], kev_set={"CVE-2024-1234"}, epss_map={"CVE-2024-1234": 0.8})
    intel = enriched[0].details["intel"]
    assert intel["cves"] == ["CVE-2024-1234"]
    assert intel["cwes"] == ["CWE-89"]
    assert intel["kev"] is True
    assert intel["risk_score"] == 10.0


def test_api_assess_openapi_and_jwt(tmp_path):
    spec = {
        "openapi": "3.0.0",
        "servers": [{"url": "http://api.example.com"}],
        "paths": {
            "/users": {
                "post": {"summary": "Create user"},
            }
        },
    }
    spec_path = tmp_path / "openapi.json"
    spec_path.write_text(json.dumps(spec), encoding="utf-8")
    eps, findings = api_assess.audit_api_spec(spec_path)
    assert len(eps) == 1
    assert len(findings) == 2

    hdr = base64.urlsafe_b64encode(b'{"alg":"none"}').decode().rstrip("=")
    pld = base64.urlsafe_b64encode(b'{"sub":"123"}').decode().rstrip("=")
    jwt_findings = api_assess.audit_jwt(f"{hdr}.{pld}.")
    assert len(jwt_findings) == 2
    assert any(f.severity == "critical" for f in jwt_findings)


def test_cicd_gate_and_compliance():
    f_old = Finding("vulnerability", "a", "Old", "critical", "nuclei", {}, "", "t")
    f_new = Finding("secret", "b", "AWS Key", "high", "gitleaks", {}, "", "t")

    gate_fail = cicd.evaluate_gate([f_old, f_new], max_critical=0)
    assert gate_fail.passed is False
    assert gate_fail.exit_code == 1

    gate_base = cicd.evaluate_gate([f_old, f_new], max_critical=0, max_high=1, baseline=[f_old])
    assert gate_base.passed is True
    assert gate_base.exit_code == 0

    redacted = compliance.redact_secrets("Authorization: Bearer secret123 token=AKIAIOSFODNN7EXAMPLE")
    assert "secret123" not in redacted
    assert "AKIAIOSFODNN7EXAMPLE" not in redacted

    mapped = compliance.map_finding_compliance(f_new)
    assert mapped["mitre"] == ["T1552-Unsecured Credentials"]


def test_plugin_sdk_and_dfir(tmp_path, monkeypatch):
    _isolate_home(tmp_path, monkeypatch)

    class GoodAdapter:
        metadata = plugin_sdk.PluginMetadata("demo", "1.0.0", "1.0", "python3")

        def build_argv(self, target: str, options: dict | None = None) -> list[str]:
            return ["python3", "-V"]

        def parse_output(self, raw: str, timestamp: str) -> list[Finding]:
            return []

    class BadAdapter(GoodAdapter):
        metadata = plugin_sdk.PluginMetadata("bad", "1.0.0", "2.0", "python3")

    reg = plugin_sdk.PluginRegistry()
    reg.register(GoodAdapter())
    assert reg.is_installed("demo") is True
    with pytest.raises(ValueError):
        reg.register(BadAdapter())

    case = dfir.create_case("incident-1", "Phishing triage")
    sample = tmp_path / "alert.log"
    sample.write_text("suspicious login\n", encoding="utf-8")
    art = dfir.ingest_artifact(case, sample)
    assert len(art.sha256) == 64
    reloaded = dfir.load_case("incident-1")
    assert reloaded is not None
    assert len(reloaded.timeline) == 1


def test_integrations_and_appsec_catalog(tmp_path, monkeypatch):
    from noxentra import integrations, toolbox

    _isolate_home(tmp_path, monkeypatch)
    e = engagement.create("acme-int", targets=["https://api.example.com"])
    fs = [
        Finding("vulnerability", "https://api.example.com", "SQLi", "high", "nuclei", {"evidence_id": "ev-1"}, "", "t"),
        Finding("subdomain", "api.example.com", "api.example.com", "info", "subfinder", {}, "", "t"),
    ]
    jira_issues = integrations.build_jira_issues(e, fs, project_key="APPSEC")
    assert len(jira_issues) == 1
    assert jira_issues[0]["fields"]["project"]["key"] == "APPSEC"

    dd = integrations.build_defectdojo_payload(e, fs)
    assert len(dd["findings"]) == 2
    assert dd["findings"][0]["severity"] == "High"

    sent: list[tuple[str, dict]] = []
    monkeypatch.setattr(integrations, "_post_json", lambda url, payload, headers, timeout=10: sent.append((url, payload)) or 200)
    rc = integrations.notify_webhook("https://hooks.example.com/notify", event="done", engagement_name="acme-int", summary="ok")
    assert rc == 200
    assert sent[0][1]["status"] == "completed"

    titles = {t.TITLE for cat in toolbox.all_tools for t in getattr(cat, "TOOLS", [])}
    assert {"Bandit (Python Security Linter)", "detect-secrets (Secret Detection)", "Schemathesis (OpenAPI & GraphQL Tester)", "Semgrep (Static Code Scanner)", "OSV-Scanner (Dependency Vuln Scanner)"}.issubset(titles)
