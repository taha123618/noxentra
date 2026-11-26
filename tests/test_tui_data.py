from noxentra.tui import data


def test_categories_nonempty_and_shaped():
    cats = data.categories()
    assert len(cats) > 1
    c = cats[0]
    assert c.title and isinstance(c.icon, str) and c.count >= 0


def test_tools_in_first_category():
    cats = data.categories()
    tools = data.tools_in(cats[0].index)
    assert isinstance(tools, list)
    if tools:
        t = tools[0]
        assert t.title
        assert isinstance(t.installed, bool)
        assert t.obj is not None  # the live engine instance for actions


def test_tool_at_round_trips():
    cats = data.categories()
    for ci, c in enumerate(cats):
        tools = data.tools_in(c.index)
        if tools:
            got = data.tool_at(c.index, tools[0].index)
            assert got.title == tools[0].title
            break


def test_tools_in_no_probe_skips_is_installed_and_probe_installed_resolves(monkeypatch):
    calls = 0

    class _FakeTool:
        TITLE = "FakeTool"
        DESCRIPTION = "desc"
        PROJECT_URL = "https://example.com"

        def is_installed(self):
            nonlocal calls
            calls += 1
            return True

    monkeypatch.setattr(data, "_active_tools", lambda _idx: [_FakeTool()])
    rows = data.tools_in(0, probe=False)
    assert calls == 0
    assert len(rows) == 1
    assert rows[0].installed is False

    states = data.probe_installed(rows)
    assert calls == 1
    assert states == [True]
