"""Goal screen: AI goal planner (/goal) with live streamed step execution."""
import threading

from textual import work
from textual.app import ComposeResult
from textual.widgets import Input, OptionList, Static
from textual.widgets.option_list import Option

from noxentra import ai_goal
from noxentra.tui import glyphs
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.widgets.live_panel import LivePanel
from noxentra.tui.widgets.permission import PermissionModal


class GoalScreen(NoxentraScreen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("c", "cancel_run", "Cancel"),
    ]
    LIST_ID = "goal-steps"
    PROMPT_PLACEHOLDER = "enter an authorized objective (e.g. 'scan 10.0.0.1') and press ⏎…"

    def __init__(self):
        self._plan: ai_goal.Plan | None = None
        super().__init__()

    def content(self) -> ComposeResult:
        ol = OptionList(*self.options(""), id=self.LIST_ID)
        ol.can_focus = False
        yield ol
        yield LivePanel(prefix="goal")
        yield Static(
            " type an objective · ↑↓ move · ⏎ run step · c cancel · ← esc back",
            id="nx-hint",
        )
        prompt = Input(placeholder=self.PROMPT_PLACEHOLDER, id="nx-prompt")
        prompt.border_title = glyphs.PROMPT
        yield prompt

    def _panel(self) -> LivePanel:
        return self.query_one(LivePanel)

    def options(self, needle: str = "") -> list[Option]:
        if self._plan is None or not self._plan.steps:
            return [Option("  Type an objective below and press ⏎ to draft a plan", id="__hint__")]
        return [
            Option(
                f"{glyphs.INSTALLED if s.installed else glyphs.NOT_INSTALLED}  "
                f"{' '.join(s.argv)}   —  {s.why}",
                id=f"s:{i}",
            )
            for i, s in enumerate(self._plan.steps)
        ]

    def action_cancel_run(self) -> None:
        self._panel().cancel()

    def on_input_changed(self, event: Input.Changed) -> None:
        v = event.value
        if v.startswith("/"):
            self._ensure_palette().filter(v[1:])
        else:
            self._remove_palette()

    def on_input_submitted(self, event: Input.Submitted) -> None:
        pal = self._palette()
        if pal is not None:
            super().on_input_submitted(event)
            return
        obj = event.value.strip()
        if obj:
            self._draft_plan(obj)
            return
        ol = self._list()
        if ol.highlighted is not None:
            self.open_selected(ol.get_option_at_index(ol.highlighted).id)

    @work(thread=True, exit_on_error=False)
    def _draft_plan(self, objective: str) -> None:
        self.app.call_from_thread(self._panel().set_indeterminate, f"⠋ Drafting plan for '{objective}'…")
        plan_ = ai_goal.plan(objective, ai_goal._toolbox())
        self.app.call_from_thread(self._apply_plan, objective, plan_)

    def _apply_plan(self, objective: str, plan_: ai_goal.Plan | None) -> None:
        ol = self._list()
        ol.clear_options()
        if plan_ is None or not plan_.steps:
            self._plan = None
            self._panel().set_idle("○ No plan generated", progress=0)
            ol.add_options([Option(f"  No plan generated for '{objective}' (configure AI via /config)", id="__empty__")])
            ol.highlighted = 0
            return
        self._plan = plan_
        self._panel().set_idle(f"✔ Planned {len(plan_.steps)} step(s)", progress=100)
        ol.add_options(self.options())
        ol.highlighted = 0
        self.query_one("#nx-prompt", Input).value = ""

    def open_selected(self, option_id: str) -> None:
        if not option_id.startswith("s:") or self._plan is None:
            return
        if self._panel().running:
            self.app.notify("A step is already running — press 'c' to cancel.", severity="warning")
            return
        idx = int(option_id.split(":", 1)[1])
        step = self._plan.steps[idx]
        if not step.installed:
            self.app.notify(f"{step.tool} is not installed on PATH", title="Missing tool", severity="warning")
            return
        self._confirm_and_run(step, idx + 1, len(self._plan.steps))

    @work
    async def _confirm_and_run(self, step: ai_goal.Step, n: int, total: int) -> None:
        cmd_str = " ".join(step.argv)
        if await self.app.push_screen_wait(PermissionModal(f"Run {step.tool}: {cmd_str}?")) == "no":
            return
        stop_event = self._panel().start(
            f"step {n}/{total}: {cmd_str}",
            banner=f"─ step {n}/{total} ─ {cmd_str}",
        )
        self._run_step_worker(step, n, total, stop_event)

    @work(thread=True, exit_on_error=False)
    def _run_step_worker(
        self, step: ai_goal.Step, n: int, total: int, stop_event: threading.Event
    ) -> None:
        import subprocess

        ws = ai_goal._workspace()
        captured: list[str] = []
        rc = 0
        err = ""
        try:
            proc = subprocess.Popen(
                step.argv,
                cwd=str(ws),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                bufsize=1,
                errors="replace",
            )

            def _watch():
                while proc.poll() is None:
                    if stop_event.wait(0.1):
                        try:
                            proc.terminate()
                        except OSError:
                            pass
                        break

            threading.Thread(target=_watch, daemon=True).start()
            if proc.stdout is not None:
                for line in proc.stdout:
                    clean = line.rstrip("\r\n")
                    captured.append(clean)
                    self.app.call_from_thread(self._panel().append_line, clean)
            rc = proc.wait()
            if stop_event.is_set() and rc == 0:
                rc = 130
            ai_goal._audit(ws, f"step {n} exit {rc}")
            (ws / f"step-{n}-{ai_goal._slug(step.tool)}.txt").write_text(
                "\n".join(captured), encoding="utf-8"
            )
        except OSError as exc:
            rc = 1
            err = str(exc)
            ai_goal._audit(ws, f"step {n} launch-failed: {exc}")
        self.app.call_from_thread(self._panel().finish, rc, err, stop_event.is_set())
