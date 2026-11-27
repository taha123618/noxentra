from noxentra import engagement, report
from noxentra.findings import Finding, save_findings


def _root(tmp_path, monkeypatch):
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)

def test_generate_report(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])
    save_findings(e.findings_file, [
        Finding("subdomain", "a.example.com", "a.example.com", "info", "subfinder", {}, "", "T"),
        Finding("vulnerability", "https://a.example.com/.git/", "Exposed .git", "high",
                "nuclei", {"template_id": "exposed-git"}, "", "T"),
    ])
    path = report.generate_report(e)
    text = path.read_text()
    assert path == e.report_file
    assert "# Engagement: acme" in text
    assert "Exposed .git" in text
    assert "high" in text
    assert "a.example.com" in text

def test_generate_report_empty(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("empty")
    text = report.generate_report(e).read_text()
    assert "No findings" in text


def test_generate_html_report_escapes_and_summarizes(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])
    save_findings(e.findings_file, [
        Finding("vulnerability", "https://example.com/?q=<script>", "XSS <img src=x>", "high",
                "nuclei", {"template_id": "xss"}, "", "T"),
    ])
    out = report.generate_html_report(e)
    body = out.read_text(encoding="utf-8")
    assert out.name == "report.html"
    assert "XSS &lt;img src=x&gt;" in body
    assert "<script>alert" not in body
    assert 'data-sev="high"' in body


def test_generate_sarif_report_valid_v210(tmp_path, monkeypatch):
    import json

    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])
    save_findings(e.findings_file, [
        Finding("vulnerability", "https://example.com/.git/", "Exposed .git", "critical",
                "nuclei", {"template_id": "exposed-git"}, "", "T"),
        Finding("subdomain", "api.example.com", "api.example.com", "info",
                "subfinder", {}, "", "T"),
    ])
    out = report.generate_sarif_report(e)
    data = json.loads(out.read_text(encoding="utf-8"))
    assert data["version"] == "2.1.0"
    results = data["runs"][0]["results"]
    assert len(results) == 2
    assert results[0]["ruleId"] == "exposed-git"
    assert results[0]["level"] == "error"
    assert results[1]["level"] == "note"
