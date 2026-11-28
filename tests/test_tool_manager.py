"""Tests for ToolManager and privilege-prefix helpers."""

from __future__ import annotations

import subprocess

from noxentra import os_detect
from noxentra.tools.tool_manager import UpdateTool


def test_update_sys_uses_list_form_without_shell(monkeypatch):
    calls: list[tuple[list[str], dict]] = []

    def fake_run(argv, **kwargs):
        calls.append((argv, kwargs))
        return subprocess.CompletedProcess(argv, 0)

    monkeypatch.setattr(subprocess, "run", fake_run)
    monkeypatch.setattr(os_detect.CURRENT_OS, "pkg_manager", "brew")
    monkeypatch.setattr(os_detect.CURRENT_OS, "system", "macos")

    UpdateTool().update_sys()

    assert calls == [
        (["brew", "update"], {"check": False}),
        (["brew", "upgrade"], {"check": False}),
    ]
    for _argv, kwargs in calls:
        assert kwargs.get("shell") is not True


def test_priv_argv_respects_os_info_is_root_on_linux(monkeypatch):
    import os

    monkeypatch.setattr(os, "geteuid", lambda: 1000)
    root_linux = os_detect.OSInfo(system="linux", pkg_manager="apt-get", is_root=True)
    user_linux = os_detect.OSInfo(system="linux", pkg_manager="apt-get", is_root=False)
    assert os_detect.priv_argv(["apt-get", "update"], os_info=root_linux) == ["apt-get", "update"]
    assert os_detect.priv_argv(["apt-get", "update"], os_info=user_linux)[1:] == ["apt-get", "update"]
