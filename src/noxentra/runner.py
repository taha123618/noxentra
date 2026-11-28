"""Unified list-form subprocess runner with streaming, timeout, and cancel escalation."""
import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path


@dataclass
class RunResult:
    """Outcome of a list-form subprocess execution."""

    returncode: int
    stdout: str
    stderr: str
    timed_out: bool = False
    cancelled: bool = False


def _terminate_gracefully(proc: subprocess.Popen[str]) -> None:
    """Send SIGTERM, wait briefly, and escalate to SIGKILL if still alive."""
    if proc.poll() is not None:
        return
    try:
        proc.terminate()
    except OSError:
        return
    try:
        proc.wait(timeout=0.3)
    except subprocess.TimeoutExpired:
        try:
            proc.kill()
        except OSError:
            pass


def run_streaming(
    argv: list[str],
    *,
    cwd: Path | str | None = None,
    stdin_text: str = "",
    timeout: float | None = None,
    stop_event: threading.Event | None = None,
    on_line: Callable[[str], None] | None = None,
    merge_stderr: bool = False,
) -> RunResult:
    """Execute `argv` list-form (shell=False) with live line callback, timeout, and cancel."""
    proc = subprocess.Popen(
        argv,
        cwd=str(cwd) if cwd is not None else None,
        stdin=subprocess.PIPE if stdin_text else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT if merge_stderr else subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )

    if proc.stdin is not None:
        def _feed() -> None:
            try:
                proc.stdin.write(stdin_text)  # type: ignore[union-attr]
                proc.stdin.close()            # type: ignore[union-attr]
            except OSError:
                pass
        threading.Thread(target=_feed, daemon=True).start()

    out_lines: list[str] = []
    err_lines: list[str] = []
    timed_out = threading.Event()
    cancelled = threading.Event()
    done_evt = threading.Event()

    timer: threading.Timer | None = None
    if timeout is not None and timeout > 0:
        def _on_timeout() -> None:
            if proc.poll() is None:
                timed_out.set()
                _terminate_gracefully(proc)
        timer = threading.Timer(timeout, _on_timeout)
        timer.daemon = True
        timer.start()

    if stop_event is not None:
        def _watch_cancel() -> None:
            while not done_evt.is_set() and proc.poll() is None:
                if stop_event.wait(0.1):
                    cancelled.set()
                    _terminate_gracefully(proc)
                    break
        threading.Thread(target=_watch_cancel, daemon=True).start()

    def _drain_stderr() -> None:
        if proc.stderr is not None:
            for line in proc.stderr:
                err_lines.append(line.rstrip("\r\n"))

    err_thread: threading.Thread | None = None
    if not merge_stderr and proc.stderr is not None:
        err_thread = threading.Thread(target=_drain_stderr, daemon=True)
        err_thread.start()

    try:
        if proc.stdout is not None:
            for line in proc.stdout:
                clean = line.rstrip("\r\n")
                out_lines.append(clean)
                if on_line is not None:
                    on_line(clean)
        rc = proc.wait()
    finally:
        done_evt.set()
        if timer is not None:
            timer.cancel()
        if err_thread is not None:
            err_thread.join(timeout=2)

    is_cancelled = cancelled.is_set() or (stop_event is not None and stop_event.is_set())
    if is_cancelled and rc == 0:
        rc = 130
    return RunResult(
        returncode=rc,
        stdout="\n".join(out_lines),
        stderr="\n".join(err_lines),
        timed_out=timed_out.is_set(),
        cancelled=is_cancelled,
    )
