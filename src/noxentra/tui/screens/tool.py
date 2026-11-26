"""Tool detail screen: live streamed execution with status, progress bar, and cancel."""
import threading

from textual import work
from textual.app import ComposeResult
from textual.widgets import OptionList, Static
from textual.widgets.option_list import Option

from noxentra import core
from noxentra.core import Noxentra
from noxentra.tui import glyphs, working
from noxentra.tui.data import ToolRow
from noxentra.tui.screens.base import NoxentraScreen
from noxentra.tui.widgets.edit_modal import EditModal
from noxentra.tui.widgets.live_panel import LivePanel
from noxentra.tui.widgets.permission import PermissionModal

_GATED = ("run", "install", "uninstall")


class ToolScreen(NoxentraScreen):
    BINDINGS = [
        ("escape", "app.pop_screen", "Back"),
        ("left", "app.pop_screen", "Back"),
        ("c", "cancel_run", "Cancel"),
    ]

    def __init__(self, row: ToolRow):
        self._row = row
        super().__init__()

    def _detail_text(self) -> str:
        r = self._row
        state = f"{glyphs.INSTALLED} installed" if r.installed else f"{glyphs.NOT_INSTALLED} not installed"
        lines = [f" {r.title}   {state}", f" {r.description}"]
        if r.url:
            lines.append(f" {r.url}")
        usage = getattr(r.obj, "USAGE", None) or ()
        if usage:
            label, cmd = usage[0]
            lines.append(f" e.g. {label}: {cmd}")
        return "\n".join(lines)

    def _default_custom_cmd(self) -> str:
        usage = getattr(self._row.obj, "USAGE", None) or ()
        if usage:
            return str(usage[0][1])
        run_cmds = getattr(self._row.obj, "RUN_COMMANDS", None) or ()
        return str(run_cmds[0]) if run_cmds else ""

    def content(self) -> ComposeResult:
        yield Static(self._detail_text(), id="tool-detail")
        yield OptionList(
            Option(f"{glyphs.RUN} Run", id="run"),
            Option("✎ Run with args…", id="run_custom"),
            Option("↻ Install", id="install"),
            Option("⧉ Open repo", id="open"),
            Option("⌫ Uninstall", id="uninstall"),
            Option("← Back", id="back"),
            id="tool-actions",
        )
        yield LivePanel(prefix="tool")
        yield Static(f" {glyphs.PROMPT} ↑↓ move · ⏎ select · c cancel · ← esc back", id="nx-hint")

    def on_mount(self) -> None:
        pass

    def _panel(self) -> LivePanel:
        return self.query_one(LivePanel)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        action = event.option.id
        if action == "back":
            self.app.pop_screen()
        elif action == "open":
            self._open_repo()
        elif action == "run_custom":
            self._prompt_custom_command()
        elif action in _GATED:
            self._run_action(action)  # fire the worker; must NOT await push_screen_wait here

    def action_cancel_run(self) -> None:
        self._panel().cancel()

    def _open_repo(self) -> None:
        import webbrowser
        url = (self._row.url or "").strip()
        if url.lower().startswith(("http://", "https://")):
            webbrowser.open_new_tab(url)

    @work(exit_on_error=False)
    async def _prompt_custom_command(self) -> None:
        if self._panel().running:
            self.app.notify("A command is already running — press 'c' to cancel.", severity="warning")
            return
        cmd = await self.app.push_screen_wait(EditModal("command", self._default_custom_cmd()))
        if not cmd or not cmd.strip():
            return
        cmd = cmd.strip()
        answer = await self.app.push_screen_wait(PermissionModal(f"Run: {cmd}?"))
        if answer == "no":
            return
        self._start_live(f"running {cmd}", lambda: core._run_shell(cmd))

    def _uses_raw_tty(self, action: str) -> bool:
        obj = self._row.obj
        if not isinstance(obj, Noxentra):
            return True
        if action == "run":
            return type(obj).run is not Noxentra.run
        if action == "install":
            return type(obj).install is not Noxentra.install
        if action == "uninstall":
            return type(obj).uninstall is not Noxentra.uninstall
        return False

    @work(exit_on_error=False)
    async def _run_action(self, action: str) -> None:
        if self._panel().running:
            self.app.notify("A command is already running — press 'c' to cancel.", severity="warning")
            return
        answer = await self.app.push_screen_wait(PermissionModal(f"{action} {self._row.title}?"))
        if answer == "no":
            return
        fn = getattr(self._row.obj, action)
        if self._uses_raw_tty(action):
            with self.app.suspend():  # drop to raw terminal for custom interactive tools
                try:
                    print(working.line(f"running {self._row.title}"))
                    fn()
                except SystemExit:
                    pass  # a tool quitting itself must not quit the TUI
                except BaseException:
                    self.app.bell()
            self._refresh_install_state()
            return

        label = f"{action}ing {self._row.title}" if action != "run" else f"running {self._row.title}"
        self._start_live(label, fn, warn_uninstalled=(action == "run" and not self._row.installed))

    def _start_live(self, label: str, fn, warn_uninstalled: bool = False) -> None:
        warn = (
            f"⚠ {self._row.title} is not installed yet — select 'Install' or 'Run with args…' if this fails."
            if warn_uninstalled
            else ""
        )
        stop_event = self._panel().start(label, banner=working.line(label), warn=warn)
        self._execute_worker(fn, stop_event)

    @work(thread=True, exit_on_error=False)
    def _execute_worker(self, fn, stop_event: threading.Event) -> None:
        rc = 0
        err = ""
        try:
            with core.live_execution(
                lambda ln: self.app.call_from_thread(self._panel().append_line, ln),
                stop_event,
                on_progress=lambda ln: self.app.call_from_thread(self._panel().update_progress_line, ln),
            ):
                fn()
                rc = core.last_exit_code()
        except SystemExit as exc:
            rc = exc.code if isinstance(exc.code, int) else 0
        except BaseException as exc:
            rc = 1
            err = str(exc)
        self.app.call_from_thread(self._on_finished, rc, err, stop_event.is_set())

    def _on_finished(self, rc: int, err: str, cancelled: bool) -> None:
        self._panel().finish(rc, err=err, cancelled=cancelled)
        self._refresh_install_state()

    def _refresh_install_state(self) -> None:
        try:
            self._row.installed = bool(self._row.obj.is_installed())
        except Exception:
            pass
        self.query_one("#tool-detail", Static).update(self._detail_text())
