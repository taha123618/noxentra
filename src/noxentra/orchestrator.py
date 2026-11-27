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


def list_pipelines() -> list[dict[str, str]]:
    """Return available pipelines sorted by name as `{name, description}` dicts."""
    items: list[dict[str, str]] = []
    for path in sorted(PIPELINES_DIR.glob("*.yaml")):
        data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        items.append({
            "name": str(data.get("name") or path.stem),
            "description": str(data.get("description") or ""),
        })
    return items


def pipeline_preflight(name: str) -> list[dict[str, object]]:
    """Return per-step tool availability `[{tool, installed, path}, ...]` for pipeline `name`."""
    steps = load_pipeline(name).get("steps", [])
    report: list[dict[str, object]] = []
    for step in steps:
        tool = str(step["tool"])
        resolved = shutil.which(tool) or ""
        report.append({"tool": tool, "installed": bool(resolved), "path": resolved})
    return report


def _resolve_wordlist() -> str:
    """Locate a standard system web wordlist, falling back to the bundled minimal list."""
    candidates = (
        Path("/usr/share/wordlists/dirb/common.txt"),
        Path("/usr/share/seclists/Discovery/Web-Content/common.txt"),
        Path("/opt/homebrew/share/wordlists/dirb/common.txt"),
        PIPELINES_DIR / "common_paths.txt",
    )
    for cand in candidates:
        if cand.is_file():
            return str(cand)
    return str(PIPELINES_DIR / "common_paths.txt")


def _expand_args(args: list[str]) -> list[str]:
    """Expand runtime placeholders such as `{wordlist}` in pipeline step args."""
    if not any("{wordlist}" in a for a in args):
        return list(args)
    wl = _resolve_wordlist()
    return [a.replace("{wordlist}", wl) for a in args]


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


def _run_streaming(
    cmd: list[str],
    stdin_text: str,
    tool: str,
    emit,
    stop_event: threading.Event | None = None,
) -> subprocess.CompletedProcess:
    """Run `cmd` via Popen, streaming stdout lines live while enforcing `STEP_TIMEOUT` and `stop_event`."""
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

    if stop_event is not None:
        def _watch_stop():
            while proc.poll() is None:
                if stop_event.wait(0.1):
                    try:
                        proc.terminate()
                    except OSError:
                        pass
                    break
        threading.Thread(target=_watch_stop, daemon=True).start()

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


def _exec_cmd(
    cmd: list[str],
    stdin_text: str,
    tool: str,
    emit,
    stream: bool,
    stop_event: threading.Event | None = None,
) -> subprocess.CompletedProcess:
    if stream and subprocess.run is _ORIG_SUBPROCESS_RUN:
        return _run_streaming(cmd, stdin_text, tool, emit, stop_event=stop_event)
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
    stop_event: threading.Event | None = None,
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
        if stop_event is not None and stop_event.is_set():
            e.log(f"cancelled pipeline '{pipeline_name}' before step {step['tool']}")
            _emit("[yellow]■ Pipeline cancelled.[/yellow]")
            break
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
        step_args = _expand_args(step["args"])
        per_flag = step.get("per_target_flag")
        per_suffix = step.get("per_target_suffix", "")
        try:
            if per_flag and items:
                workers = max(1, min(int(step.get("workers", 4)), len(items)))
                raw_chunks: list[str] = []
                with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
                    futs = [
                        pool.submit(
                            _exec_cmd,
                            [
                                tool,
                                *step_args,
                                per_flag,
                                f"{item.rstrip('/')}{per_suffix}" if per_suffix else item,
                            ],
                            "",
                            tool,
                            _emit,
                            cb is not None,
                            stop_event,
                        )
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
                proc = _exec_cmd([tool, *step_args], stdin, tool, _emit, cb is not None, stop_event)
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

    existing = findings_mod.load_findings(e.findings_file)
    merged, new_count = findings_mod.diff_findings(existing, all_findings)
    findings_mod.save_findings(e.findings_file, merged)
    e.add_run({
        "pipeline": pipeline_name,
        "at": ts,
        "findings": len(all_findings),
        "new_findings": new_count,
    })
    _emit(f"[green]✔ {pipeline_name}: +{new_count} new, {len(merged)} total finding(s)[/green]")
    return merged
