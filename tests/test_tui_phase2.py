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


async def _run_slash(pilot, cmd: str) -> None:
    inp = pilot.app.screen.query_one("#nx-prompt", Input)
    inp.focus()
    inp.value = cmd
    for _ in range(20):
        await pilot.pause()
        if pilot.app.screen.query("CommandPalette"):
            break
    await pilot.press("enter")


def test_recommend_screen_resolves_and_opens_tool(monkeypatch):
    from noxentra import ai_recommend
    monkeypatch.setattr(ai_recommend, "ask", lambda _prompt: None)

    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            await _run_slash(pilot, "/recommend")
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
            await _run_slash(pilot, "/report")
            await _until(pilot, ReportScreen)

            ol = pilot.app.screen.query_one("#report-engagements", OptionList)
            assert ol.option_count == 1
            await pilot.press("enter")  # drill into report actions
            await pilot.pause()
            assert ol.option_count == 3
            await pilot.press("enter")  # Export deterministic report (report.md)
            await pilot.pause()
            assert e.report_file.exists()
            assert "msg" in seen and "Saved" in seen["msg"][0][0]

    asyncio.run(run())


def test_report_screen_ai_summary_and_draft(tmp_path, monkeypatch):
    from noxentra import ai_report, ai_summary

    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    engagement.create("acme", targets=["example.com"])
    monkeypatch.setattr(ai_summary, "summarize", lambda _e: "2 open ports found")
    draft = tmp_path / "acme" / "report.draft.md"
    monkeypatch.setattr(ai_report, "draft_report", lambda _e: draft)

    async def run():
        async with NoxentraApp().run_test(size=(100, 30)) as pilot:
            await _until(pilot, MainScreen)
            msgs = []
            pilot.app.notify = lambda *a, **k: msgs.append((a, k))
            await _run_slash(pilot, "/report")
            await _until(pilot, ReportScreen)

            await pilot.press("enter")  # select engagement
            await pilot.pause()
            await pilot.press("down", "enter")  # AI Summary
            for _ in range(40):
                await pilot.pause()
                if any("2 open ports found" in m[0][0] for m in msgs):
                    break
            assert any("2 open ports found" in m[0][0] for m in msgs)

            await pilot.press("down", "enter")  # AI Report Draft
            for _ in range(40):
                await pilot.pause()
                if any("report.draft.md" in m[0][0] for m in msgs):
                    break
            assert any("report.draft.md" in m[0][0] for m in msgs)

    asyncio.run(run())
