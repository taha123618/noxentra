"""Goal screen: AI goal planner (/goal) with explicit permission gate per step."""
from textual import work
from textual.widgets import Input
from textual.widgets.option_list import Option

from noxentra import ai_goal
from noxentra.tui import glyphs
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.widgets.permission import PermissionModal


class GoalScreen(NoxentraScreen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    LIST_ID = "goal-steps"
    PROMPT_PLACEHOLDER = "enter an authorized objective (e.g. 'scan 10.0.0.1') and press ⏎…"

    def __init__(self):
        self._plan: ai_goal.Plan | None = None
        super().__init__()

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
        plan_ = ai_goal.plan(objective, ai_goal._toolbox())
        self.app.call_from_thread(self._apply_plan, objective, plan_)

    def _apply_plan(self, objective: str, plan_: ai_goal.Plan | None) -> None:
        ol = self._list()
        ol.clear_options()
        if plan_ is None or not plan_.steps:
            self._plan = None
            ol.add_options([Option(f"  No plan generated for '{objective}' (configure AI via /config)", id="__empty__")])
            ol.highlighted = 0
            return
        self._plan = plan_
        ol.add_options(self.options())
        ol.highlighted = 0
        self.query_one("#nx-prompt", Input).value = ""

    def open_selected(self, option_id: str) -> None:
        if not option_id.startswith("s:") or self._plan is None:
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
        if not await self.app.push_screen_wait(PermissionModal(step.tool, f"Run: {cmd_str}")):
            return
        ws = ai_goal._workspace()
        with self.app.suspend():
            ai_goal._run_step(step, n, total, ws)
            input("\nPress Enter to return to noxentra…")
