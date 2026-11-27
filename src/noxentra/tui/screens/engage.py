"""Engage screen (/engage): manage engagements and run recon pipelines live."""
import threading
from typing import ClassVar

from rich.errors import MarkupError
from rich.text import Text
from textual import work
from textual.app import ComposeResult
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from noxentra import engagement, orchestrator, report
from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.screens.report import ReportScreen
from noxentra.tui.widgets.create_engagement_modal import CreateEngagementModal
from noxentra.tui.widgets.live_panel import LivePanel
from noxentra.tui.widgets.permission import PermissionModal


def _strip_markup(msg: str) -> str:
    try:
        return Text.from_markup(msg).plain
    except MarkupError:
        return msg


class EngageScreen(NoxentraScreen):
    BINDINGS: ClassVar = [
        ("escape", "back_or_pop", "Back"),
        ("c", "cancel_run", "Cancel"),
        ("n", "new_engagement", "New"),
    ]
    LIST_ID = "engage-list"
    PROMPT_PLACEHOLDER = "filter engagements or /commands…"

    def __init__(self):
        self._rows = data.engagements()
        self._selected: data.EngagementRow | None = None
        super().__init__()

    def content(self) -> ComposeResult:
        ol = OptionList(*self.options(""), id=self.LIST_ID)
        ol.can_focus = False
        yield ol
        yield LivePanel(prefix="engage")
        yield Static(
            " ↑↓ move · ⏎ select · n new engagement · c cancel run · ← esc back",
            id="nx-hint",
        )
        prompt = Input(placeholder=self.PROMPT_PLACEHOLDER, id="nx-prompt")
        prompt.border_title = glyphs.PROMPT
        yield prompt

    def _panel(self) -> LivePanel:
        return self.query_one(LivePanel)

    def action_cancel_run(self) -> None:
        self._panel().cancel()

    def action_new_engagement(self) -> None:
        if self._panel().running:
            self.app.notify("Finish or cancel the active pipeline first.", severity="warning")
            return
        self._create_engagement_flow()

    def action_back_or_pop(self) -> None:
        if self._selected is not None:
            self._selected = None
            self.query_one("#nx-prompt", Input).value = ""
            self._reload("")
        else:
            self.app.pop_screen()

    def _reload(self, needle: str = "") -> None:
        ol = self._list()
        ol.clear_options()
        ol.add_options(self.options(needle))
        ol.highlighted = 0 if ol.option_count else None

    def options(self, needle: str = "") -> list[Option]:
        n = needle.lower().strip()
        if self._selected is not None:
            opts = []
            for p in orchestrator.list_pipelines():
                checks = orchestrator.pipeline_preflight(p["name"])
                ready = sum(1 for c in checks if c["installed"])
                badge = f"{ready}/{len(checks)} ready"
                label = f"{glyphs.RUN}  Run {p['name']} ({badge})   —  {p['description']}"
                if not n or n in p["name"].lower() or n in p["description"].lower():
                    opts.append(Option(label, id=f"p:{p['name']}"))
            opts.extend([
                Option(f"{glyphs.RUN}  Export report (report.md)", id="act:report"),
                Option(f"{glyphs.RUN}  Open /report screen", id="act:open_report"),
                Option("← Back to engagements", id="act:engagements"),
            ])
            return opts

        opts = [Option("＋  Create new engagement…", id="__create__")]
        for r in self._rows:
            if n and n not in r.name.lower():
                continue
            opts.append(
                Option(
                    f"{glyphs.RUN}  {r.name}   ·  {r.targets_count} targets · {r.findings_count} findings",
                    id=f"e:{r.name}",
                )
            )
        return opts

    def open_selected(self, option_id: str) -> None:
        if option_id == "__create__":
            self.action_new_engagement()
            return
        if option_id == "act:engagements":
            self._selected = None
            self.query_one("#nx-prompt", Input).value = ""
            self._reload("")
            return
        if option_id == "act:report" and self._selected is not None:
            out = report.generate_report(self._selected.obj)
            self.app.notify(f"Saved {out}", title=f"Report: {self._selected.name}")
            return
        if option_id == "act:open_report":
            self.app.push_screen(ReportScreen())
            return
        if option_id.startswith("p:") and self._selected is not None:
            if self._panel().running:
                self.app.notify("A pipeline is already running — press 'c' to cancel.", severity="warning")
                return
            pipeline_name = option_id.split(":", 1)[1]
            checks = orchestrator.pipeline_preflight(pipeline_name)
            if checks and not any(c["installed"] for c in checks):
                missing = ", ".join(str(c["tool"]) for c in checks)
                self.app.notify(
                    f"No tools installed for '{pipeline_name}' (missing: {missing})",
                    title="Missing pipeline tools",
                    severity="warning",
                )
                return
            self._confirm_and_run(self._selected.obj, pipeline_name)
            return
        if option_id.startswith("e:"):
            name = option_id.split(":", 1)[1]
            row = next((r for r in self._rows if r.name == name), None)
            if row is not None:
                self._selected = row
                self.query_one("#nx-prompt", Input).value = ""
                self._reload("")
                self._panel().set_idle(
                    f"● {row.name}: {', '.join(row.obj.targets)} ({row.findings_count} findings)",
                    progress=0,
                )

    @work
    async def _create_engagement_flow(self) -> None:
        spec = await self.app.push_screen_wait(CreateEngagementModal())
        if not spec:
            return
        existing = engagement.load(spec["name"])
        if existing is not None:
            existing.targets = spec["targets"]
            if spec["scope_in"] is not None:
                existing.scope_in = spec["scope_in"]
            existing.scope_out = spec["scope_out"]
            existing.save()
        else:
            engagement.create(
                spec["name"],
                targets=spec["targets"],
                scope_in=spec["scope_in"],
                scope_out=spec["scope_out"],
            )
        self._rows = data.engagements()
        self._selected = next((r for r in self._rows if r.name == spec["name"]), None)
        self.query_one("#nx-prompt", Input).value = ""
        self._reload("")
        if self._selected is not None:
            self._panel().set_idle(
                f"✔ Created {self._selected.name}: {', '.join(self._selected.obj.targets)}",
                progress=0,
            )

    @work
    async def _confirm_and_run(self, eng: engagement.Engagement, pipeline_name: str) -> None:
        targets = ", ".join(eng.targets)
        if await self.app.push_screen_wait(
            PermissionModal(f"Run pipeline '{pipeline_name}' on {eng.name} ({targets})?")
        ) == "no":
            return
        stop_event = self._panel().start(
            f"{pipeline_name} on {eng.name}",
            banner=f"─ {pipeline_name} · targets: {targets} ─",
        )
        self._run_pipeline_worker(eng, pipeline_name, stop_event)

    @work(thread=True, exit_on_error=False)
    def _run_pipeline_worker(
        self,
        eng: engagement.Engagement,
        pipeline_name: str,
        stop_event: threading.Event,
    ) -> None:
        def _emit(msg: str) -> None:
            self.app.call_from_thread(self._panel().append_line, _strip_markup(msg))

        rc = 0
        err = ""
        try:
            found = orchestrator.run_pipeline(
                eng,
                pipeline_name,
                on_progress=_emit,
                stop_event=stop_event,
            )
            new_n = eng.runs[-1].get("new_findings", 0) if eng.runs else 0
            self.app.call_from_thread(
                self._panel().append_line,
                f"✔ +{new_n} new, {len(found)} total deduplicated findings",
            )
            if stop_event.is_set():
                rc = 130
        except (OSError, ValueError, KeyError) as exc:
            rc = 1
            err = str(exc)
        self.app.call_from_thread(self._finish_run, eng.name, rc, err, stop_event.is_set())

    def _finish_run(self, name: str, rc: int, err: str, cancelled: bool) -> None:
        self._panel().finish(rc, err=err, cancelled=cancelled)
        self._rows = data.engagements()
        if self._selected is not None and self._selected.name == name:
            refreshed = next((r for r in self._rows if r.name == name), None)
            if refreshed is not None:
                self._selected = refreshed
        self._reload(self.query_one("#nx-prompt", Input).value)
