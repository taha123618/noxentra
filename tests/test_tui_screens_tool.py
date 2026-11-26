import asyncio
import contextlib
import sys
from typing import ClassVar

from textual.app import App
from textual.widgets import Input, OptionList, ProgressBar, RichLog, Static

from noxentra.core import Noxentra
from noxentra.tui.data import ToolRow
from noxentra.tui.screens.tool import ToolScreen
from noxentra.tui.widgets.edit_modal import EditModal
from noxentra.tui.widgets.permission import PermissionModal


class _Fake:
    ran = False

    def run(self):
        self.ran = True


def _row():
    return ToolRow(index=0, title="Sublist3r", description="Enumerate subdomains",
                   url="", installed=True, obj=_Fake())


class _App(App):
    def __init__(self, row):
        self._row = row
        super().__init__()

    def on_mount(self) -> None:
        self.push_screen(ToolScreen(self._row))


async def _until_screen(pilot, kind):
    for _ in range(40):
        await pilot.pause()
        if isinstance(pilot.app.screen, kind):
            return
    raise AssertionError(f"{kind.__name__} never appeared")


def test_structure_option_ids():
    async def run():
        async with _App(_row()).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ids = [ol.get_option_at_index(i).id for i in range(ol.option_count)]
            assert set(ids) == {"run", "run_custom", "install", "open", "uninstall", "back"}

    asyncio.run(run())


def test_permission_gate_runs_fn():
    # HeadlessDriver.can_suspend is False, so real App.suspend() raises
    # SuspendNotSupported under run_test(); override it with a no-op so fn() still
    # fires. Production code keeps the real suspend() to give tools a TTY.
    # PermissionModal highlights "Yes" (index 0) on mount with nothing pre-pressed,
    # so a single "enter" presses it → "yes" and proceeds past the gate.
    row = _row()

    async def run():
        async with _App(row).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            pilot.app.suspend = lambda: contextlib.nullcontext()
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ol.focus()
            ol.highlighted = ol.get_option_index("run")
            await pilot.press("enter")
            await _until_screen(pilot, PermissionModal)
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause()
                if row.obj.ran:
                    break
            assert row.obj.ran

    asyncio.run(run())


def test_back_pops_screen():
    async def run():
        async with _App(_row()).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ol.focus()
            ol.highlighted = ol.get_option_index("back")
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause()
                if not isinstance(pilot.app.screen, ToolScreen):
                    break
            assert not isinstance(pilot.app.screen, ToolScreen)

    asyncio.run(run())


class _LiveTool(Noxentra):
    TITLE = "Gobuster"
    DESCRIPTION = "Directory brute-forcer"
    RUN_COMMANDS: ClassVar = [
        f'"{sys.executable}" -c "import time; print(\'found /admin\', flush=True); time.sleep(0.05); print(\'found /api\', flush=True)"'
    ]


class _SlowTool(Noxentra):
    TITLE = "SlowGobuster"
    DESCRIPTION = "Long-running tool"
    RUN_COMMANDS: ClassVar = [f'"{sys.executable}" -c "import time; print(\'started\', flush=True); time.sleep(10)"']


def test_live_execution_streams_output_and_updates_status():
    tool = _LiveTool(installable=False, runnable=True)
    row = ToolRow(index=0, title=tool.TITLE, description=tool.DESCRIPTION, url="", installed=True, obj=tool)

    async def run():
        async with _App(row).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ol.focus()
            ol.highlighted = ol.get_option_index("run")
            await pilot.press("enter")
            await _until_screen(pilot, PermissionModal)
            await pilot.press("enter")

            status = pilot.app.screen.query_one("#tool-status", Static)
            for _ in range(80):
                await pilot.pause(0.05)
                if "Completed (exit 0)" in str(status.render()):
                    break
            assert "Completed (exit 0)" in str(status.render())
            pb = pilot.app.screen.query_one("#tool-progress", ProgressBar)
            assert pb.progress == 100
            log = pilot.app.screen.query_one("#tool-log", RichLog)
            text = "\n".join(line.text for line in log.lines)
            assert "found /admin" in text
            assert "found /api" in text

    asyncio.run(run())


def test_live_execution_cancel_stops_process():
    tool = _SlowTool(installable=False, runnable=True)
    row = ToolRow(index=0, title=tool.TITLE, description=tool.DESCRIPTION, url="", installed=True, obj=tool)

    async def run():
        async with _App(row).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ol.focus()
            ol.highlighted = ol.get_option_index("run")
            await pilot.press("enter")
            await _until_screen(pilot, PermissionModal)
            await pilot.press("enter")

            log = pilot.app.screen.query_one("#tool-log", RichLog)
            for _ in range(60):
                await pilot.pause(0.05)
                if any("started" in ln.text for ln in log.lines):
                    break
            await pilot.press("c")
            status = pilot.app.screen.query_one("#tool-status", Static)
            for _ in range(60):
                await pilot.pause(0.05)
                if "Cancelled" in str(status.render()):
                    break
            assert "Cancelled" in str(status.render())

    asyncio.run(run())


def test_run_custom_command_streams_in_tool_screen():
    tool = _LiveTool(installable=False, runnable=True)
    row = ToolRow(index=0, title=tool.TITLE, description=tool.DESCRIPTION, url="", installed=True, obj=tool)

    async def run():
        async with _App(row).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ol.focus()
            ol.highlighted = ol.get_option_index("run_custom")
            await pilot.press("enter")
            await _until_screen(pilot, EditModal)
            inp = pilot.app.screen.query_one("#edit-input", Input)
            inp.value = f'"{sys.executable}" -c "print(\'custom-ok\')"'
            await pilot.press("enter")
            await _until_screen(pilot, PermissionModal)
            await pilot.press("enter")

            status = pilot.app.screen.query_one("#tool-status", Static)
            for _ in range(60):
                await pilot.pause(0.05)
                if "Completed (exit 0)" in str(status.render()):
                    break
            assert "Completed (exit 0)" in str(status.render())
            log = pilot.app.screen.query_one("#tool-log", RichLog)
            assert any("custom-ok" in ln.text for ln in log.lines)

    asyncio.run(run())


class _ProgressTool(Noxentra):
    TITLE = "GobusterProgress"
    DESCRIPTION = "Simulated Gobuster progress"
    RUN_COMMANDS: ClassVar = [
        f'"{sys.executable}" -c "import sys, time; sys.stdout.write(\'Progress: 250 / 1000 (25.0%)\\r\'); sys.stdout.flush(); time.sleep(0.1); print(\'/admin (Status: 301)\', flush=True)"'
    ]


def test_pty_carriage_return_updates_progress_bar_live():
    tool = _ProgressTool(installable=False, runnable=True)
    row = ToolRow(index=0, title=tool.TITLE, description=tool.DESCRIPTION, url="", installed=True, obj=tool)

    async def run():
        async with _App(row).run_test() as pilot:
            await _until_screen(pilot, ToolScreen)
            ol = pilot.app.screen.query_one("#tool-actions", OptionList)
            ol.focus()
            ol.highlighted = ol.get_option_index("run")
            await pilot.press("enter")
            await _until_screen(pilot, PermissionModal)
            await pilot.press("enter")

            status = pilot.app.screen.query_one("#tool-status", Static)
            seen_pct = False
            for _ in range(80):
                await pilot.pause(0.02)
                if "25.0%" in str(status.render()):
                    seen_pct = True
                if "Completed (exit 0)" in str(status.render()):
                    break
            assert seen_pct
            assert "Completed (exit 0)" in str(status.render())
            log = pilot.app.screen.query_one("#tool-log", RichLog)
            assert any("/admin (Status: 301)" in ln.text for ln in log.lines)

    asyncio.run(run())
