"""Report screen: browse engagements, inspect findings, and export Markdown/HTML/SARIF/AI reports."""
import json
from typing import ClassVar

from textual import work
from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static
from textual.widgets.option_list import Option

from noxentra import ai_report, ai_summary, findings, report
from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen


class FindingDetailModal(ModalScreen[None]):
    """Displays full details and raw output for a selected finding."""

    BINDINGS: ClassVar = [("escape", "dismiss", "Close"), ("enter", "dismiss", "Close")]

    def __init__(self, finding: findings.Finding):
        self._finding = finding
        super().__init__()

    def compose(self) -> ComposeResult:
        f = self._finding
        details = json.dumps(f.details or {}, indent=2)
        body = (
            f"● [{f.severity}] {f.name}\n"
            f"Kind: {f.kind} · Tool: {f.source_tool}\n"
            f"Target: {f.target}\n"
            f"Timestamp: {f.timestamp}\n\n"
            f"Details:\n{details}\n\n"
            f"Raw:\n{f.raw or '(empty)'}"
        )
        with Vertical(id="finding-detail-box"):
            yield Static(body, id="finding-detail-text", markup=False)
            yield Button("Close (Esc)", id="finding-close")

    def on_button_pressed(self, event: Button.Pressed) -> None:
        self.dismiss(None)


class ReportScreen(NoxentraScreen):
    BINDINGS: ClassVar = [("escape", "back_or_pop", "Back")]
    LIST_ID = "report-engagements"
    PROMPT_PLACEHOLDER = "filter engagements…"

    def __init__(self):
        self._rows = data.engagements()
        self._selected: data.EngagementRow | None = None
        self._browsing_findings = False
        self._findings: list[findings.Finding] = []
        super().__init__()

    def action_back_or_pop(self) -> None:
        if self._browsing_findings:
            self._browsing_findings = False
            self.query_one("#nx-prompt", Input).value = ""
            self._reload("")
        elif self._selected is not None:
            self._selected = None
            self.query_one("#nx-prompt", Input).value = ""
            self._reload("")
        else:
            self.app.pop_screen()

    def _reload(self, needle: str) -> None:
        ol = self._list()
        ol.clear_options()
        ol.add_options(self.options(needle))
        ol.highlighted = 0 if ol.option_count else None

    def options(self, needle: str = "") -> list[Option]:
        n = needle.lower().strip()
        if self._browsing_findings and self._selected is not None:
            if not self._findings:
                return [Option("  No findings recorded for this engagement yet.", id="__empty__")]
            opts = []
            for idx, f in enumerate(self._findings):
                hay = f"{f.severity} {f.kind} {f.source_tool} {f.name} {f.target}".lower()
                if n and n not in hay:
                    continue
                opts.append(Option(
                    f"[{f.severity}] {f.name}  ·  {f.target}  ({f.source_tool})",
                    id=f"f:{idx}",
                ))
            return opts or [Option(f"  No findings matching '{needle}'", id="__empty__")]

        if self._selected is not None:
            count = self._selected.findings_count
            return [
                Option(f"{glyphs.RUN}  Export deterministic report (report.md)", id="act:report"),
                Option(f"{glyphs.RUN}  AI Summary (triage findings)", id="act:ai-summary"),
                Option(f"{glyphs.RUN}  AI Report Draft (report.draft.md)", id="act:ai-report"),
                Option(f"{glyphs.RUN}  Export HTML report (report.html)", id="act:html"),
                Option(f"{glyphs.RUN}  Export SARIF report (report.sarif.json)", id="act:sarif"),
                Option(f"{glyphs.RUN}  Browse findings ({count})", id="act:findings"),
            ]
        if not self._rows:
            return [
                Option(
                    "  No engagements yet — open /engage or run: noxentra --engagement <name> --targets <target>",
                    id="__empty__",
                )
            ]
        opts = []
        for r in self._rows:
            if n and n not in r.name.lower():
                continue
            opts.append(Option(
                f"{glyphs.RUN}  {r.name}   ·  {r.targets_count} targets · {r.findings_count} findings",
                id=r.name,
            ))
        if not opts:
            opts.append(Option(f"  No engagements matching '{needle}'", id="__empty__"))
        return opts

    def open_selected(self, option_id: str) -> None:
        if option_id == "__empty__":
            return
        if option_id.startswith("f:") and self._browsing_findings:
            idx = int(option_id.split(":", 1)[1])
            if 0 <= idx < len(self._findings):
                self.app.push_screen(FindingDetailModal(self._findings[idx]))
            return
        if option_id.startswith("act:") and self._selected is not None:
            action = option_id.split(":", 1)[1]
            e = self._selected.obj
            if action == "report":
                out = report.generate_report(e)
                self.app.notify(f"Saved {out}", title=f"Report: {e.name}")
            elif action == "html":
                out = report.generate_html_report(e)
                self.app.notify(f"Saved {out}", title=f"HTML Report: {e.name}")
            elif action == "sarif":
                out = report.generate_sarif_report(e)
                self.app.notify(f"Saved {out}", title=f"SARIF Report: {e.name}")
            elif action == "findings":
                raw_findings = findings.load_findings(e.findings_file)
                self._findings = sorted(
                    raw_findings,
                    key=lambda f: (report._SEV_ORDER.get(f.severity, 9), f.kind, f.target),
                )
                self._browsing_findings = True
                self.query_one("#nx-prompt", Input).value = ""
                self._reload("")
            elif action == "ai-summary":
                self._run_ai_summary(e)
            elif action == "ai-report":
                self._run_ai_report(e)
            return
        row = next((r for r in self._rows if r.name == option_id), None)
        if row is None:
            return
        self._selected = row
        self.query_one("#nx-prompt", Input).value = ""
        self._reload("")

    @work(thread=True, exit_on_error=False)
    def _run_ai_summary(self, e) -> None:
        text = ai_summary.summarize(e)
        if text:
            self.app.call_from_thread(self.app.notify, text[:240], title=f"AI Summary: {e.name}")
        else:
            self.app.call_from_thread(
                self.app.notify,
                "AI model unavailable or no findings to summarize (configure via /config).",
                title=f"AI Summary: {e.name}",
                severity="warning",
            )

    @work(thread=True, exit_on_error=False)
    def _run_ai_report(self, e) -> None:
        out = ai_report.draft_report(e)
        if out:
            self.app.call_from_thread(self.app.notify, f"Saved {out}", title=f"AI Draft: {e.name}")
        else:
            self.app.call_from_thread(
                self.app.notify,
                "AI model unavailable or no findings (configure via /config).",
                title=f"AI Draft: {e.name}",
                severity="warning",
            )
