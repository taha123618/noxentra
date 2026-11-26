"""Tests for TUI parity screens: /tags, /skill, /find, /goal."""
import asyncio

from textual.widgets import Input, OptionList

from noxentra import ai_goal, discover
from noxentra.tui.app import NoxentraApp
from noxentra.tui.screens.find import FindScreen
from noxentra.tui.screens.goal import GoalScreen
from noxentra.tui.screens.main import MainScreen
from noxentra.tui.screens.skill import SkillScreen
from noxentra.tui.screens.tags import TagsScreen
from noxentra.tui.screens.tool import ToolScreen


async def _until(pilot, kind):
    for _ in range(40):
        await pilot.pause()
        if isinstance(pilot.app.screen, kind):
            return
    raise AssertionError(f"never reached {kind.__name__}: on {type(pilot.app.screen).__name__}")


async def _run_slash(pilot, cmd: str) -> None:
    inp = pilot.app.screen.query_one("#nx-prompt", Input)
    inp.focus()
    inp.value = cmd
    for _ in range(20):
        await pilot.pause()
        if pilot.app.screen.query("CommandPalette"):
            break
    await pilot.press("enter")


def test_tags_screen_drills_into_tool():
    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            await _run_slash(pilot, "/tags")
            await _until(pilot, TagsScreen)

            ol = pilot.app.screen.query_one("#tags-list", OptionList)
            assert ol.option_count > 10
            await pilot.press("enter")  # drill into first tag
            await pilot.pause()
            assert pilot.app.screen._selected_tag is not None
            await pilot.press("enter")  # open first tool in that tag
            await _until(pilot, ToolScreen)
            assert isinstance(pilot.app.screen, ToolScreen)

    asyncio.run(run())


def test_skill_screen_renders_playbook():
    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            await _run_slash(pilot, "/skill")
            await _until(pilot, SkillScreen)
            assert pilot.app.screen.query_one("#skill-body")

    asyncio.run(run())


def test_find_screen_searches_and_saves_repo(tmp_path, monkeypatch):
    repo = discover.Repo(
        full_name="acme/subfinder-mini",
        description="Fast subdomain finder",
        url="https://github.com/acme/subfinder-mini",
        stars=420,
        forks=10,
        pushed_at="2026-01-01T00:00:00Z",
        created_at="2025-01-01T00:00:00Z",
        archived=False,
        fork=False,
        license="MIT",
        language="Go",
        topics=["recon"],
        owner="acme",
        owner_type="User",
    )
    res = discover.DiscoveryResult(
        need="subdomains",
        rewrite=discover.Rewrite(tags=["recon"]),
        repos=[repo],
    )
    monkeypatch.setattr(discover, "find", lambda need: res)
    monkeypatch.setattr(discover, "_found_path", lambda: tmp_path / "found.yaml")

    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            await _run_slash(pilot, "/find")
            await _until(pilot, FindScreen)

            find_inp = pilot.app.screen.query_one("#nx-prompt", Input)
            find_inp.value = "subdomains"
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause()
                if pilot.app.screen._repos:
                    break
            assert len(pilot.app.screen._repos) == 1
            await pilot.press("enter")
            await pilot.pause()
            assert (tmp_path / "found.yaml").exists()

    asyncio.run(run())


def test_goal_screen_drafts_plan(monkeypatch):
    fake_plan = ai_goal.Plan(
        target="10.0.0.1",
        steps=[ai_goal.Step(tool="nmap", argv=["nmap", "-sV", "10.0.0.1"], why="service scan", installed=True)],
    )
    monkeypatch.setattr(ai_goal, "plan", lambda objective, toolbox: fake_plan)

    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            await _run_slash(pilot, "/goal")
            await _until(pilot, GoalScreen)

            goal_inp = pilot.app.screen.query_one("#nx-prompt", Input)
            goal_inp.value = "scan 10.0.0.1"
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause()
                if pilot.app.screen._plan is not None:
                    break
            ol = pilot.app.screen.query_one("#goal-steps", OptionList)
            assert ol.option_count == 1

    asyncio.run(run())
