"""Tags screen: browse all catalog tags with counts, drill into tools for a tag."""
from textual.widgets import Input
from textual.widgets.option_list import Option

from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.screens.tool import ToolScreen


class TagsScreen(NoxentraScreen):
    BINDINGS = [("escape", "back_or_pop", "Back")]
    LIST_ID = "tags-list"
    PROMPT_PLACEHOLDER = "filter tags…"

    def __init__(self):
        self._tags = data.tags_summary()
        self._selected_tag: str | None = None
        super().__init__()

    def action_back_or_pop(self) -> None:
        if self._selected_tag is not None:
            self._selected_tag = None
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
        if self._selected_tag is not None:
            hits = next((h for t, h in self._tags if t == self._selected_tag), [])
            return [
                Option(f"{glyphs.RUN}  {h.title}   ·  {h.cat_label}", id=f"t:{h.cat_index}:{h.tool_index}")
                for h in hits
                if not n or n in h.title.lower() or n in h.cat_label.lower()
            ]
        return [
            Option(f"  #{tag}   ({len(hits)})", id=f"tag:{tag}")
            for tag, hits in self._tags
            if not n or n in tag
        ]

    def open_selected(self, option_id: str) -> None:
        if option_id.startswith("tag:"):
            self._selected_tag = option_id.split(":", 1)[1]
            self.query_one("#nx-prompt", Input).value = ""
            self._reload("")
        elif option_id.startswith("t:"):
            _, ci, ti = option_id.split(":")
            self.app.push_screen(ToolScreen(data.tool_at(int(ci), int(ti))))
