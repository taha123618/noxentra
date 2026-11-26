"""Sequential, stdin-driven pipeline runner. list-form subprocess only."""
import contextlib
import shutil
import subprocess
import threading
from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import urlparse

import yaml

import noxentra.findings as findings_mod
from noxentra.engagement import Engagement

PIPELINES_DIR = Path(__file__).resolve().parent / "pipelines"
STEP_TIMEOUT = 1800  # 30 min per step; ponytail: bump if a step legitimately runs longer


def load_pipeline(name: str) -> dict:
    if not name or name in (".", "..") or "/" in name or "\\" in name:
        raise ValueError(f"Invalid pipeline name: {name!r}")
    root = PIPELINES_DIR.resolve()
    target = (root / f"{name}.yaml").resolve()
    if not target.is_relative_to(root):
        raise ValueError(f"Invalid pipeline name: {name!r}")
    return yaml.safe_load(target.read_text())


def _host_of(line: str) -> str:
    """Extract the hostname from a forward line that may be a bare host or a URL."""
    if "://" in line:
        return urlparse(line).hostname or line
    return line.split("/")[0].split(":")[0]


_progress_tls = threading.local()


@contextlib.contextmanager
def live_progress(fn):
    """Temporarily route `run_pipeline` step status updates to `fn` on this thread."""
    prev = getattr(_progress_tls, "fn", None)
    _progress_tls.fn = fn
    try:
        yield
    finally:
        _progress_tls.fn = prev


def run_pipeline(
    e: Engagement,
    pipeline_name: str = "recon",
    on_progress=None,
) -> list[findings_mod.Finding]:
    pipeline = load_pipeline(pipeline_name)
    e.raw_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    all_findings: list[findings_mod.Finding] = []
    forward: list[str] = list(e.targets)
    steps = pipeline["steps"]
    total = len(steps)
    cb = on_progress or getattr(_progress_tls, "fn", None)

    def _emit(msg: str) -> None:
        if cb is not None:
            cb(msg)

    for idx, step in enumerate(steps, start=1):
        tool = step["tool"]
        if shutil.which(tool) is None:
            e.log(f"skip {tool}: not installed (install it from the menu)")
            _emit(f"[yellow][{idx}/{total}] skip {tool} (not installed)[/yellow]")
            if not step.get("fallback_to_targets"):
                forward = []
            continue
        _emit(f"[cyan][{idx}/{total}] running {tool}…[/cyan]")
        mode = step["input"]
        if mode == "hosts":
            items = [_host_of(t) for t in e.targets]
        elif mode == "targets":
            items = list(e.targets)
        else:
            items = list(forward)
            if not items and step.get("fallback_to_targets"):
                items = list(e.targets)
        stdin = "\n".join(items)
        try:
            proc = subprocess.run([tool, *step["args"]], input=stdin,
                                  capture_output=True, text=True, timeout=STEP_TIMEOUT,
                                  encoding="utf-8", errors="replace", check=False)  # a stray non-UTF8 byte must not abort the run
            raw = proc.stdout
            if proc.returncode != 0:
                tail = (proc.stderr or "").strip().splitlines()[-3:]
                e.log(f"{tool}: exit {proc.returncode}; stderr: {' | '.join(tail)}")
        except subprocess.TimeoutExpired as exc:
            raw = exc.stdout or ""                       # keep records emitted before the deadline
            if isinstance(raw, bytes):
                raw = raw.decode("utf-8", "replace")
            (e.workspace / step["output"]).write_text(raw, encoding="utf-8")
            parsed, _ = findings_mod.PARSERS[step["parser"]](raw, ts)
            all_findings.extend(parsed)
            e.log(f"timeout {tool} after {STEP_TIMEOUT}s; salvaged {len(parsed)} finding(s)")
            forward = []                                 # incomplete step → don't forward to the next
            continue
        except OSError as exc:
            e.log(f"error {tool}: {exc}")
            forward = []
            continue
        (e.workspace / step["output"]).write_text(raw, encoding="utf-8")
        parsed, forward = findings_mod.PARSERS[step["parser"]](raw, ts)
        if e.scope_out:
            kept = []
            for line in forward:
                if e.is_excluded(_host_of(line)):
                    e.log(f"scope-out: dropped discovered {line} (matches exclusion)")
                else:
                    kept.append(line)
            forward = kept
        e.log(f"{tool}: {len(parsed)} findings, {len(forward)} forwarded")
        _emit(f"[green][{idx}/{total}] {tool}: {len(parsed)} finding(s), {len(forward)} forwarded[/green]")
        all_findings.extend(parsed)

    findings_mod.save_findings(e.findings_file, all_findings)
    e.add_run({"pipeline": pipeline_name, "at": ts, "findings": len(all_findings)})
    return all_findings
