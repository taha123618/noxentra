"""findings.json -> Markdown, HTML, and SARIF v2.1.0 reports."""
import html
import json
from pathlib import Path

from noxentra.constants import VERSION
from noxentra.engagement import Engagement
from noxentra.findings import load_findings

_KIND_TITLES = {
    "subdomain": "Subdomains",
    "service": "Live Services",
    "vulnerability": "Vulnerabilities",
    "misconfiguration": "Misconfigurations",
    "iam-risk": "IAM Risks",
}
_SEV_ORDER = {"critical": 0, "high": 1, "medium": 2, "low": 3, "info": 4, "unknown": 5}
_SARIF_LEVEL = {"critical": "error", "high": "error", "medium": "warning",
                "low": "note", "info": "note", "unknown": "note"}


def _cell(s: str) -> str:
    return str(s).replace("|", "\\|").replace("\n", " ")


def render_report(e: Engagement, findings=None) -> str:
    """Deterministic facts-table report as a Markdown string (no file write).

    The single source of report truth: findings/severities/targets/tools come
    straight from ``findings.json``. AI4 reuses this verbatim as its verified
    appendix so the model never has to emit the facts. Pass ``findings`` to reuse an
    already-loaded snapshot (keeps narrative and appendix consistent); else re-reads.
    """
    if findings is None:
        findings = load_findings(e.findings_file)
    lines: list[str] = [f"# Engagement: {e.name}", ""]
    lines.append(f"- **Targets:** {', '.join(e.targets) or '(none)'}")
    lines.append(f"- **Scope in:** {', '.join(e.scope_in) or '(none)'}")
    lines.append(f"- **Scope out:** {', '.join(e.scope_out) or '(none)'}")
    lines.append(f"- **Created:** {e.created}")
    lines.append(f"- **Total findings:** {len(findings)}")
    lines.append("")

    if not findings:
        lines.append("_No findings recorded yet._")
        return "\n".join(lines)

    for kind, title in _KIND_TITLES.items():
        group = [f for f in findings if f.kind == kind]
        if not group:
            continue
        lines.append(f"## {title} ({len(group)})")
        lines.append("")
        lines.append("| Severity | Name | Target | Tool |")
        lines.append("|---|---|---|---|")
        for f in sorted(group, key=lambda f: _SEV_ORDER.get(f.severity, 9)):
            lines.append(f"| {f.severity} | {_cell(f.name)} | {_cell(f.target)} | {f.source_tool} |")
        lines.append("")

    return "\n".join(lines)


def render_html(e: Engagement, findings=None) -> str:
    """Render a self-contained single-file HTML report with severity cards and live filtering."""
    if findings is None:
        findings = load_findings(e.findings_file)
    ordered = sorted(findings, key=lambda f: (_SEV_ORDER.get(f.severity, 9), f.kind, f.target))
    counts = {sev: sum(1 for f in ordered if f.severity == sev)
              for sev in ("critical", "high", "medium", "low", "info")}

    cards = "\n".join(
        f'<div class="card sev-{sev}" data-sev="{sev}">'
        f'<div class="count">{counts[sev]}</div><div class="label">{sev.upper()}</div></div>'
        for sev in ("critical", "high", "medium", "low", "info")
    )

    rows = "\n".join(
        f'<tr data-sev="{html.escape(f.severity, quote=True)}">'
        f'<td><span class="badge sev-{html.escape(f.severity, quote=True)}">'
        f'{html.escape(f.severity)}</span></td>'
        f'<td>{html.escape(f.kind)}</td>'
        f'<td>{html.escape(f.name)}</td>'
        f'<td><code>{html.escape(f.target)}</code></td>'
        f'<td>{html.escape(f.source_tool)}</td>'
        f'</tr>'
        for f in ordered
    )
    table_body = rows or '<tr><td colspan="5" class="empty">No findings recorded yet.</td></tr>'

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Noxentra Report — {html.escape(e.name)}</title>
<style>
:root {{ --bg:#0d1117; --panel:#161b22; --border:#30363d; --text:#e6edf3; --muted:#8b949e; --accent:#58a6ff; }}
body {{ font-family: system-ui, -apple-system, sans-serif; background: var(--bg); color: var(--text); margin: 0; padding: 2rem; }}
h1 {{ margin: 0 0 .5rem; }}
.meta {{ color: var(--muted); margin-bottom: 1.5rem; font-size: .95rem; }}
.cards {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(120px, 1fr)); gap: .75rem; margin-bottom: 1.5rem; }}
.card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 8px; padding: .9rem; cursor: pointer; text-align: center; }}
.card .count {{ font-size: 1.6rem; font-weight: 700; }}
.card .label {{ font-size: .75rem; color: var(--muted); letter-spacing: .06em; }}
.controls {{ display: flex; gap: .75rem; margin-bottom: 1rem; }}
input {{ flex: 1; background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: .55rem .8rem; }}
button {{ background: var(--panel); color: var(--text); border: 1px solid var(--border); border-radius: 6px; padding: .55rem .9rem; cursor: pointer; }}
table {{ width: 100%; border-collapse: collapse; background: var(--panel); border: 1px solid var(--border); border-radius: 8px; overflow: hidden; }}
th, td {{ text-align: left; padding: .65rem .8rem; border-bottom: 1px solid var(--border); font-size: .9rem; }}
th {{ color: var(--muted); font-weight: 600; }}
.badge {{ padding: .15rem .5rem; border-radius: 999px; font-size: .78rem; font-weight: 600; text-transform: uppercase; }}
.sev-critical .count, .badge.sev-critical {{ color: #ff7b72; }}
.sev-high .count, .badge.sev-high {{ color: #ffa657; }}
.sev-medium .count, .badge.sev-medium {{ color: #d29922; }}
.sev-low .count, .badge.sev-low {{ color: #58a6ff; }}
.sev-info .count, .badge.sev-info {{ color: #8b949e; }}
.empty {{ text-align: center; color: var(--muted); padding: 2rem; }}
</style>
</head>
<body>
<h1>Engagement: {html.escape(e.name)}</h1>
<div class="meta">
  <strong>Targets:</strong> {html.escape(", ".join(e.targets) or "(none)")} &middot;
  <strong>Scope in:</strong> {html.escape(", ".join(e.scope_in) or "(none)")} &middot;
  <strong>Scope out:</strong> {html.escape(", ".join(e.scope_out) or "(none)")} &middot;
  <strong>Created:</strong> {html.escape(e.created)} &middot;
  <strong>Total:</strong> {len(ordered)}
</div>
<div class="cards">{cards}</div>
<div class="controls">
  <input id="q" type="search" placeholder="Filter by severity, tool, target, or name…">
  <button id="reset" type="button">Show all</button>
</div>
<table>
  <thead><tr><th>Severity</th><th>Kind</th><th>Name</th><th>Target</th><th>Tool</th></tr></thead>
  <tbody id="rows">{table_body}</tbody>
</table>
<script>
const q = document.getElementById("q");
const rows = [...document.querySelectorAll("#rows tr[data-sev]")];
let activeSev = "";
function apply() {{
  const needle = q.value.trim().toLowerCase();
  for (const r of rows) {{
    const okSev = !activeSev || r.dataset.sev === activeSev;
    const okTxt = !needle || r.textContent.toLowerCase().includes(needle);
    r.style.display = (okSev && okTxt) ? "" : "none";
  }}
}}
q.addEventListener("input", apply);
document.getElementById("reset").addEventListener("click", () => {{ activeSev = ""; q.value = ""; apply(); }});
for (const c of document.querySelectorAll(".card[data-sev]")) {{
  c.addEventListener("click", () => {{ activeSev = (activeSev === c.dataset.sev) ? "" : c.dataset.sev; apply(); }});
}}
</script>
</body>
</html>
"""


def render_sarif(e: Engagement, findings=None) -> str:
    """Render findings as SARIF v2.1.0 JSON for GitHub Code Scanning / IDE integration."""
    if findings is None:
        findings = load_findings(e.findings_file)
    rules_map: dict[str, dict] = {}
    results: list[dict] = []
    for f in findings:
        tid = (f.details or {}).get("template_id") if isinstance(f.details, dict) else None
        rule_id = str(tid or f"{f.source_tool}/{f.kind}")
        if rule_id not in rules_map:
            rules_map[rule_id] = {
                "id": rule_id,
                "name": f.name,
                "shortDescription": {"text": f"{f.source_tool} ({f.kind})"},
            }
        results.append({
            "ruleId": rule_id,
            "level": _SARIF_LEVEL.get(f.severity, "note"),
            "message": {"text": f"[{f.severity}] {f.name} on {f.target} ({f.source_tool})"},
            "locations": [{"physicalLocation": {"artifactLocation": {"uri": f.target or e.name}}}],
            "properties": {
                "severity": f.severity,
                "kind": f.kind,
                "source_tool": f.source_tool,
                "details": f.details,
            },
        })
    sarif = {
        "$schema": "https://json.schemastore.org/sarif-2.1.0.json",
        "version": "2.1.0",
        "runs": [{
            "tool": {
                "driver": {
                    "name": "Noxentra",
                    "version": VERSION,
                    "rules": list(rules_map.values()),
                }
            },
            "results": results,
        }],
    }
    return json.dumps(sarif, indent=2)


def generate_report(e: Engagement) -> Path:
    e.report_file.write_text(render_report(e), encoding="utf-8")
    return e.report_file


def generate_html_report(e: Engagement) -> Path:
    out = e.workspace / "report.html"
    out.write_text(render_html(e), encoding="utf-8")
    return out


def generate_sarif_report(e: Engagement) -> Path:
    out = e.workspace / "report.sarif.json"
    out.write_text(render_sarif(e), encoding="utf-8")
    return out
