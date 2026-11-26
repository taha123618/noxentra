"""Pipeline runner: list-form subprocess with streaming output and optional parallel per-target execution."""
import concurrent.futures
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
_ORIG_SUBPROCESS_RUN = subprocess.run


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


def _run_streaming(cmd: list[str], stdin_text: str, tool: str, emit) -> subprocess.CompletedProcess:
    """Run `cmd` via Popen, streaming stdout lines live while enforcing `STEP_TIMEOUT`."""
    proc = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE if stdin_text else subprocess.DEVNULL,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    if proc.stdin is not None:
        def _feed():
            try:
                proc.stdin.write(stdin_text)
                proc.stdin.close()
            except OSError:
                pass
        threading.Thread(target=_feed, daemon=True).start()

    out_lines: list[str] = []
    err_lines: list[str] = []
    timed_out = threading.Event()

    def _kill_on_timeout():
        if proc.poll() is None:
            timed_out.set()
            try:
                proc.terminate()
            except OSError:
                pass

    timer = threading.Timer(STEP_TIMEOUT, _kill_on_timeout)
    timer.daemon = True
    timer.start()

    def _read_err():
        if proc.stderr is not None:
            for line in iter(proc.stderr.readline, ""):
                err_lines.append(line.rstrip("\r\n"))

    err_thread = threading.Thread(target=_read_err, daemon=True)
    err_thread.start()
    try:
        if proc.stdout is not None:
            for line in iter(proc.stdout.readline, ""):
                clean = line.rstrip("\r\n")
                out_lines.append(clean)
                emit(f"[dim]  [{tool}] {clean}[/dim]")
        rc = proc.wait()
        err_thread.join(timeout=1.0)
    finally:
        timer.cancel()

    stdout = "\n".join(out_lines) + ("\n" if out_lines else "")
    stderr = "\n".join(err_lines)
    if timed_out.is_set():
        raise subprocess.TimeoutExpired(cmd, STEP_TIMEOUT, output=stdout, stderr=stderr)
    return subprocess.CompletedProcess(cmd, rc, stdout=stdout, stderr=stderr)


def _exec_cmd(cmd: list[str], stdin_text: str, tool: str, emit, stream: bool) -> subprocess.CompletedProcess:
    if stream and subprocess.run is _ORIG_SUBPROCESS_RUN:
        return _run_streaming(cmd, stdin_text, tool, emit)
    return subprocess.run(
        cmd,
        input=stdin_text,
        capture_output=True,
        text=True,
        timeout=STEP_TIMEOUT,
        encoding="utf-8",
        errors="replace",
        check=False,
    )


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
        per_flag = step.get("per_target_flag")
        try:
            if per_flag and items:
                workers = max(1, min(int(step.get("workers", 4)), len(items)))
                raw_chunks: list[str] = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                    futs = [
                        pool.submit(_exec_cmd, [tool, *step["args"], per_flag, item], "", tool, _emit, cb is not None)
                        for item in items
                    ]
                    for fut in concurrent.futures.as_completed(futs):
                        proc = fut.result()
                        if proc.stdout:
                            raw_chunks.append(proc.stdout)
                        if proc.returncode != 0:
                            tail = (proc.stderr or "").strip().splitlines()[-3:]
                            e.log(f"{tool}: exit {proc.returncode}; stderr: {' | '.join(tail)}")
                raw = "\n".join(raw_chunks)
            else:
                stdin = "\n".join(items)
                proc = _exec_cmd([tool, *step["args"]], stdin, tool, _emit, cb is not None)
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
