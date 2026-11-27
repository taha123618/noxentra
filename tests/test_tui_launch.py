import sys
from unittest import mock

from noxentra import cli


# NOTE: cli imports get_tools_dir via `from noxentra.config import get_tools_dir`,
# so the live name is noxentra.cli.get_tools_dir (patching noxentra.config.*
# would not intercept it). ensure_user_files is called as config.ensure_user_files,
# so it is patched on the config module.
def test_default_launches_tui(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["noxentra"])
    monkeypatch.setattr("sys.stdin.isatty", lambda: True)
    monkeypatch.setattr("sys.stdout.isatty", lambda: True)
    with mock.patch("noxentra.tui.app.run") as tui, \
         mock.patch("noxentra.config.ensure_user_files"), \
         mock.patch("noxentra.cli.get_tools_dir"):
        cli.main()
    assert tui.called


def test_classic_flag_skips_tui(monkeypatch):
    monkeypatch.setattr(sys, "argv", ["noxentra", "--classic"])
    with mock.patch("noxentra.tui.app.run") as tui, \
         mock.patch("noxentra.cli.interact_menu") as classic, \
         mock.patch("noxentra.repl._use_repl", return_value=False), \
         mock.patch("noxentra.config.ensure_user_files"), \
         mock.patch("noxentra.cli.get_tools_dir"):
        cli.main()
    assert not tui.called
    assert classic.called
