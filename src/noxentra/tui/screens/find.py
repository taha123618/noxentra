"""Find screen: GitHub tool discovery (/find) with safe save to ~/.noxentra/found.yaml."""
from textual import work
from textual.widgets import Input
from textual.widgets.option_list import Option

from noxentra import discover
from noxentra.tui import glyphs
from noxentra.tui.screens.base import NoxentraScreen


class FindScreen(NoxentraScreen):
    BINDINGS = [("escape", "app.pop_screen", "Back")]
    LIST_ID = "find-results"
    PROMPT_PLACEHOLDER = "what tool are you looking for? press ⏎ to search…"

    def __init__(self):
        self._repos: list[discover.Repo] = []
        self._tags: list[str] = []
        super().__init__()

    def options(self, needle: str = "") -> list[Option]:
        if not self._repos:
            return [Option("  Type a capability (e.g. 'subdomain enum') and press ⏎", id="__hint__")]
        return [
            Option(
                f"{glyphs.RUN}  {r.full_name} ({r.stars}★)  —  {r.description[:60]}",
                id=f"r:{i}",
            )
            for i, r in enumerate(self._repos)
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
        need = event.value.strip()
        if need:
            self._run_find(need)
            return
        ol = self._list()
        if ol.highlighted is not None:
            self.open_selected(ol.get_option_at_index(ol.highlighted).id)

    @work(thread=True, exit_on_error=False)
    def _run_find(self, need: str) -> None:
        res = discover.find(need)
        self.app.call_from_thread(self._apply_results, res)

    def _apply_results(self, res: discover.DiscoveryResult) -> None:
        if res.refused:
            self.app.notify(res.refused, title="Refused", severity="warning")
            return
        self._repos = list(res.repos)
        self._tags = list(res.rewrite.tags) if res.rewrite else []
        ol = self._list()
        ol.clear_options()
        if not self._repos:
            msg = res.note or f"No GitHub repositories found for '{res.need}'."
            ol.add_options([Option(f"  {msg}", id="__empty__")])
            ol.highlighted = 0
            return
        ol.add_options(self.options())
        ol.highlighted = 0
        self.query_one("#nx-prompt", Input).value = ""

    def open_selected(self, option_id: str) -> None:
        if not option_id.startswith("r:"):
            return
        repo = self._repos[int(option_id.split(":", 1)[1])]
        saved = discover.save_repo(repo, self._tags)
        if saved:
            self.app.notify(f"Saved {repo.full_name} to {saved}", title="Added")
        else:
            self.app.notify(f"Could not save {repo.full_name}", title="Error", severity="error")
