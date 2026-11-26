import asyncio

from textual.app import App, ComposeResult

from noxentra.tui.widgets.header import Header


class _App(App):
    def compose(self) -> ComposeResult:
        yield Header("noxentra v3.1.0", "ready", 217)


def test_header_renders_title_status_count():
    async def run():
        async with _App().run_test() as pilot:
            h = pilot.app.query_one(Header)
            text = h.render().plain
            assert "noxentra v3.1.0" in text
            assert "ready" in text
            assert "217" in text

    asyncio.run(run())
