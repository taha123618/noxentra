"""`python -m noxentra` dispatches to cli.main."""
import runpy
from unittest import mock


def test_main_module_calls_cli_main():
    with mock.patch("noxentra.cli.main") as m:
        runpy.run_module("noxentra", run_name="__main__")
    assert m.called
