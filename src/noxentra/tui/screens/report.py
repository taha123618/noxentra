"""Report screen: browse engagements and export deterministic or AI-assisted reports."""
from textual import work
from textual.widgets import Input
from textual.widgets.option_list import Option

from noxentra import ai_report, ai_summary, report
from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen


class ReportScreen(NoxentraScreen):
    BINDINGS = [("escape", "back_or_pop", "Back")]
    LIST_ID = "report-engagements"
    PROMPT_PLACEHOLDER = "filter engagements…"

    def __init__(self):
        self._rows = data.engagements()
        self._selected: data.EngagementRow | None = None
        super().__init__()

    def action_back_or_pop(self) -> None:
        if self._selected is not None:
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
        if self._selected is not None:
            return [
                Option(f"{glyphs.RUN}  Export deterministic report (report.md)", id="act:report"),
                Option(f"{glyphs.RUN}  AI Summary (triage findings)", id="act:ai-summary"),
                Option(f"{glyphs.RUN}  AI Report Draft (report.draft.md)", id="act:ai-report"),
            ]
        if not self._rows:
            return [
                Option(
                    "  No engagements yet — run: noxentra --engagement <name> --targets <target>",
                    id="__empty__",
                )
            ]
        n = needle.lower().strip()
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
        if option_id.startswith("act:") and self._selected is not None:
            action = option_id.split(":", 1)[1]
            e = self._selected.obj
            if action == "report":
                out = report.generate_report(e)
                self.app.notify(f"Saved {out}", title=f"Report: {e.name}")
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
