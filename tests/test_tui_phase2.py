"""Tests for Phase-2 TUI screens: RecommendScreen (/recommend) and ReportScreen (/report)."""
import asyncio

from textual.widgets import Input, OptionList

from noxentra import engagement
from noxentra.tui.app import NoxentraApp
from noxentra.tui.screens.main import MainScreen
from noxentra.tui.screens.recommend import RecommendScreen
from noxentra.tui.screens.report import ReportScreen
from noxentra.tui.screens.tool import ToolScreen


async def _until(pilot, kind):
    for _ in range(40):
        await pilot.pause()
        if isinstance(pilot.app.screen, kind):
            return
    raise AssertionError(f"never reached {kind.__name__}: on {type(pilot.app.screen).__name__}")


def test_recommend_screen_resolves_and_opens_tool(monkeypatch):
    import noxentra.ai_recommend as ai_recommend
    monkeypatch.setattr(ai_recommend, "ask", lambda _prompt: None)

    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            inp = pilot.app.screen.query_one("#nx-prompt", Input)
            inp.value = "/recommend"
            await pilot.pause()
            await pilot.press("enter")
            await _until(pilot, RecommendScreen)

            rec_inp = pilot.app.screen.query_one("#nx-prompt", Input)
            rec_inp.value = "subdomain enumeration"
            await pilot.press("enter")
            for _ in range(40):
                await pilot.pause()
                if pilot.app.screen._hits:
                    break
            assert pilot.app.screen._hits

            ol = pilot.app.screen.query_one("#recommend-tools", OptionList)
            assert ol.option_count >= 1
            await pilot.press("enter")
            await _until(pilot, ToolScreen)
            assert isinstance(pilot.app.screen, ToolScreen)

    asyncio.run(run())


def test_report_screen_exports_engagement_report(tmp_path, monkeypatch):
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    e = engagement.create("acme", targets=["example.com"])

    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            seen = {}
            pilot.app.notify = lambda *a, **k: seen.setdefault("msg", (a, k))
            inp = pilot.app.screen.query_one("#nx-prompt", Input)
            inp.value = "/report"
            await pilot.pause()
            await pilot.press("enter")
            await _until(pilot, ReportScreen)

            ol = pilot.app.screen.query_one("#report-engagements", OptionList)
            assert ol.option_count == 1
            await pilot.press("enter")
            await pilot.pause()
            assert e.report_file.exists()
            assert "msg" in seen and "Saved" in seen["msg"][0][0]

    asyncio.run(run())
