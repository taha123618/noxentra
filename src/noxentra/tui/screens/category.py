"""Category screen: tools in a category with async install-mark probing."""
from textual import work
from textual.widgets import Input
from textual.widgets.option_list import Option

from noxentra.tui import data, glyphs
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.screens.tool import ToolScreen


class CategoryScreen(NoxentraScreen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    LIST_ID = "cat-tools"
    PROMPT_PLACEHOLDER = "type to filter tools…"

    def __init__(self, cat_index: int):
        self._cat = cat_index
        # Load tool metadata immediately; probe disk/PATH off the UI thread in on_mount.
        self._rows = data.tools_in(cat_index, probe=False)
        super().__init__()

    def on_mount(self) -> None:
        super().on_mount()
        self._probe_installs()

    @work(thread=True, exit_on_error=False)
    def _probe_installs(self) -> None:
        states = data.probe_installed(self._rows)
        self.app.call_from_thread(self._apply_install_states, states)

    def _apply_install_states(self, states: list[bool]) -> None:
        for r, inst in zip(self._rows, states):
            r.installed = inst
        ol = self._list()
        cur_idx = ol.highlighted
        needle = self.query_one("#nx-prompt", Input).value if self.query("#nx-prompt") else ""
        ol.clear_options()
        ol.add_options(self.options(needle))
        if ol.option_count:
            ol.highlighted = min(cur_idx or 0, ol.option_count - 1)

    def options(self, needle: str = "") -> list[Option]:
        opts = []
        for r in self._rows:
            if needle and needle.lower() not in r.title.lower():
                continue
            mark = glyphs.INSTALLED if r.installed else glyphs.NOT_INSTALLED
            opts.append(Option(f"{mark}  {r.title}", id=str(r.index)))
        return opts

    def open_selected(self, option_id: str) -> None:
        idx = int(option_id)
        row = self._rows[idx]
        try:
            row.installed = bool(row.obj.is_installed())
        except Exception:
            pass
        self.app.push_screen(ToolScreen(row))
