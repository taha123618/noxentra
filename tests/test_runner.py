"""Tests for the unified list-form process runner."""

from __future__ import annotations

import sys
import threading

from noxentra import runner


def test_run_streaming_captures_stdout_stderr_and_lines():
    lines: list[str] = []
    res = runner.run_streaming(
        [sys.executable, "-c", "import sys; print('out1'); print('out2'); print('err1', file=sys.stderr)"],
        on_line=lines.append,
    )
    assert res.returncode == 0
    assert not res.timed_out
    assert not res.cancelled
    assert res.stdout.splitlines() == ["out1", "out2"]
    assert "err1" in res.stderr
    assert lines == ["out1", "out2"]


def test_run_streaming_cancellation_sets_cancelled_and_130():
    stop = threading.Event()
    lines: list[str] = []

    def on_line(line: str) -> None:
        lines.append(line)
        stop.set()

    res = runner.run_streaming(
        [sys.executable, "-c", "import time; print('ready', flush=True); time.sleep(10)"],
        stop_event=stop,
        on_line=on_line,
    )
    assert res.cancelled is True
    assert res.timed_out is False
    assert res.returncode != 0
    assert "ready" in lines


def test_run_streaming_timeout_sets_timed_out():
    res = runner.run_streaming(
        [sys.executable, "-c", "import time; time.sleep(10)"],
        timeout=0.15,
    )
    assert res.timed_out is True
    assert res.cancelled is False
    assert res.returncode != 0
