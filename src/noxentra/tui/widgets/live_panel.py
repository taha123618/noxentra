"""Reusable live-execution panel: animated status bar, ProgressBar, and streaming RichLog."""
import re
import threading
import time

from rich.text import Text
from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.widgets import ProgressBar, RichLog, Static

from noxentra.tui.widgets.header import Header

_SPINNER = ("⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏")
_PCT_RE = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")


class LivePanel(Vertical):
    """Displays real-time command status, progress bar, elapsed timer, and streaming log."""

    def __init__(self, prefix: str = "live"):
        self._prefix = prefix
        self.running = False
        self._stop_event: threading.Event | None = None
        self._started_at = 0.0
        self._spin_idx = 0
        self._active_label = ""
        self._last_line = ""
        self._timer = None
        super().__init__(id=f"{prefix}-panel", classes="live-panel")

    def compose(self) -> ComposeResult:
        with Horizontal(id=f"{self._prefix}-status-row", classes="live-status-row"):
            yield Static("○ Ready", id=f"{self._prefix}-status", classes="live-status")
            yield ProgressBar(
                total=100,
                show_eta=False,
                show_percentage=False,
                id=f"{self._prefix}-progress",
                classes="live-progress",
            )
        yield RichLog(
            id=f"{self._prefix}-log",
            classes="live-log",
            highlight=False,
            markup=False,
            wrap=True,
            auto_scroll=True,
        )

    def on_mount(self) -> None:
        self._timer = self.set_interval(0.1, self._tick, pause=True)

    def on_unmount(self) -> None:
        if self._stop_event is not None:
            self._stop_event.set()
        if self._timer is not None:
            self._timer.stop()

    def set_idle(self, text: str, progress: float = 0) -> None:
        self.query_one(f"#{self._prefix}-status", Static).update(text)
        self.query_one(f"#{self._prefix}-progress", ProgressBar).update(total=100, progress=progress)

    def set_indeterminate(self, text: str) -> None:
        self.query_one(f"#{self._prefix}-status", Static).update(text)
        self.query_one(f"#{self._prefix}-progress", ProgressBar).update(total=None, progress=0)

    def start(self, label: str, banner: str = "", warn: str = "") -> threading.Event:
        self.running = True
        self._stop_event = threading.Event()
        self._started_at = time.monotonic()
        self._spin_idx = 0
        self._active_label = label
        self._last_line = ""
        log = self.query_one(f"#{self._prefix}-log", RichLog)
        log.clear()
        if banner:
            log.write(Text(banner, style="bold cyan"))
        if warn:
            log.write(Text(warn, style="bold yellow"))
        self.query_one(f"#{self._prefix}-progress", ProgressBar).update(total=None, progress=0)
        self._update_status()
        if self._timer is not None:
            self._timer.resume()
        return self._stop_event

    def cancel(self) -> None:
        if self.running and self._stop_event is not None and not self._stop_event.is_set():
            self._stop_event.set()
            self.append_line("■ Cancelling execution…")

    def append_line(self, line: str) -> None:
        stripped = line.strip()
        if stripped:
            self._last_line = stripped[:70]
            self._maybe_update_pct(stripped)
        self.query_one(f"#{self._prefix}-log", RichLog).write(Text.from_ansi(line))

    def update_progress_line(self, line: str) -> None:
        """Update live status and ProgressBar from carriage-return progress output."""
        plain = Text.from_ansi(line).plain.strip()
        if not plain:
            return
        self._last_line = plain[:70]
        self._maybe_update_pct(plain)
        if self.running:
            self._update_status()

    def _maybe_update_pct(self, text: str) -> None:
        m = _PCT_RE.search(text)
        if not m:
            return
        pct = max(0.0, min(100.0, float(m.group(1))))
        self.query_one(f"#{self._prefix}-progress", ProgressBar).update(total=100, progress=pct)

    def _tick(self) -> None:
        if not self.running:
            return
        self._spin_idx = (self._spin_idx + 1) % len(_SPINNER)
        self._update_status()

    def _update_status(self) -> None:
        elapsed = time.monotonic() - self._started_at
        spin = _SPINNER[self._spin_idx]
        tail = f" · {self._last_line}" if self._last_line else ""
        self.query_one(f"#{self._prefix}-status", Static).update(
            f"{spin} {self._active_label} ({elapsed:.1f}s){tail}"
        )
        for hdr in self.screen.query(Header):
            hdr.set_status(f"running ({elapsed:.0f}s)")

    def finish(self, rc: int, err: str = "", cancelled: bool = False) -> None:
        elapsed = time.monotonic() - self._started_at
        self.running = False
        if self._timer is not None:
            self._timer.pause()
        self.query_one(f"#{self._prefix}-progress", ProgressBar).update(total=100, progress=100)
        if err:
            self.append_line(f"✘ Error: {err}")
        if cancelled:
            msg = f"■ Cancelled after {elapsed:.1f}s"
        elif rc == 0:
            msg = f"✔ Completed (exit 0) in {elapsed:.1f}s"
        else:
            msg = f"✘ Exited with code {rc} in {elapsed:.1f}s"
        self.append_line(msg)
        self.query_one(f"#{self._prefix}-status", Static).update(msg)
        for hdr in self.screen.query(Header):
            hdr.set_status("ready")
