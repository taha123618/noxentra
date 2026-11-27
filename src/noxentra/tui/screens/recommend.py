"""Recommend screen: free-text goal -> AI/offline tag matching -> ToolScreen."""
from typing import ClassVar

from textual import work
from textual.widgets import Input
from textual.widgets.option_list import Option

from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.screens.tool import ToolScreen


class RecommendScreen(NoxentraScreen):
    BINDINGS: ClassVar = [("escape", "app.pop_screen", "Back")]
    LIST_ID = "recommend-tools"
    PROMPT_PLACEHOLDER = "describe your goal (e.g. subdomain enumeration) and press ⏎…"

    def __init__(self):
        self._hits: list[data.ToolHit] = []
        self._tags: list[str] = []
        self._status = "ready"
        super().__init__()

    def status_text(self) -> str:
        return self._status

    def options(self, needle: str = "") -> list[Option]:
        if not self._hits:
            return [Option("  Type a goal below and press ⏎ for tool recommendations", id="__hint__")]
        return [
            Option(f"{glyphs.RUN}  {h.title}   ·  {h.cat_label}", id=f"t:{h.cat_index}:{h.tool_index}")
            for h in self._hits
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
        intent = event.value.strip()
        if intent:
            self._run_recommend(intent)
            return
        ol = self._list()
        if ol.highlighted is not None:
            self.open_selected(ol.get_option_at_index(ol.highlighted).id)

    @work(thread=True, exit_on_error=False)
    def _run_recommend(self, intent: str) -> None:
        tags, hits = data.recommend_tools(intent)
        self.app.call_from_thread(self._apply_results, intent, tags, hits)

    def _apply_results(self, intent: str, tags: list[str], hits: list[data.ToolHit]) -> None:
        self._tags = tags
        self._hits = hits
        ol = self._list()
        ol.clear_options()
        if not hits:
            ol.add_options([Option(f"  No tools matched '{intent}'", id="__empty__")])
            ol.highlighted = 0
            return
        ol.add_options(self.options())
        ol.highlighted = 0
        self.query_one("#nx-prompt", Input).value = ""
        if tags:
            self.app.notify(f"Matched tags: {', '.join(tags)}", title="Recommended")

    def open_selected(self, option_id: str) -> None:
        if not option_id.startswith("t:"):
            return
        _, ci, ti = option_id.split(":")
        self.app.push_screen(ToolScreen(data.tool_at(int(ci), int(ti))))
