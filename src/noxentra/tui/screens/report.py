"""Report screen: browse engagements and export deterministic Markdown reports."""
from textual.widgets.option_list import Option

from noxentra import report
from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen


class ReportScreen(NoxentraScreen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    LIST_ID = "report-engagements"
    PROMPT_PLACEHOLDER = "filter engagements…"

    def __init__(self):
        self._rows = data.engagements()
        super().__init__()

    def options(self, needle: str = "") -> list[Option]:
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
        row = next((r for r in self._rows if r.name == option_id), None)
        if row is None:
            return
        out = report.generate_report(row.obj)
        self.app.notify(f"Saved {out}", title=f"Report: {row.name}")
