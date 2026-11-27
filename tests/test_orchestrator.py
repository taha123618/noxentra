import json
import subprocess

from noxentra import engagement, orchestrator


def _root(tmp_path, monkeypatch):
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)

def test_load_pipeline_reads_yaml():
    p = orchestrator.load_pipeline("recon")
    assert p["name"] == "recon"
    assert [s["tool"] for s in p["steps"]] == ["subfinder", "httpx", "nuclei"]


def test_full_recon_pipeline_runs_nmap_on_hosts(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["10.0.0.1", "https://example.com/"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t if t == "nmap" else None)

    calls = {}
    def fake_run(cmd, input=None, **kwargs):
        calls[cmd[0]] = input
        out = "Host: 10.0.0.1 ()\tPorts: 80/open/tcp//http//nginx/\n"
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    result = orchestrator.run_pipeline(e, "full_recon")
    assert calls["nmap"] == "10.0.0.1\nexample.com"
    assert len(result) == 1
    assert result[0].source_tool == "nmap"


def test_run_pipeline_emits_progress_events(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["10.0.0.1"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t if t == "nmap" else None)

    def fake_run(cmd, input=None, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    events = []
    orchestrator.run_pipeline(e, "full_recon", on_progress=events.append)
    assert any("[1/4] running nmap" in ev for ev in events)
    assert any("skip subfinder" in ev for ev in events)

def test_run_pipeline_wires_stdin_and_normalizes(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])

    # every tool "installed"
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t)

    calls = {}
    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, **kwargs):
        tool = cmd[0]
        calls[tool] = input  # capture what each step received on stdin
        out = {
            "subfinder": "a.example.com\n",
            "httpx": json.dumps({"url": "https://a.example.com", "status_code": 200}) + "\n",
            "nuclei": json.dumps({"template-id": "x", "info": {"name": "X", "severity": "low"},
                                  "matched-at": "https://a.example.com"}) + "\n",
        }[tool]
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)

    result = orchestrator.run_pipeline(e, "recon")

    assert calls["subfinder"] == "example.com"          # targets -> stdin
    assert calls["httpx"] == "a.example.com"            # subfinder forward -> stdin
    assert calls["nuclei"] == "https://a.example.com"   # httpx bare url -> stdin
    kinds = sorted(f.kind for f in result)
    assert kinds == ["service", "subdomain", "vulnerability"]
    assert e.findings_file.exists()
    assert (e.raw_dir / "subfinder.txt").exists()

def test_run_pipeline_skips_missing_tool(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: None)  # nothing installed
    result = orchestrator.run_pipeline(e, "recon")
    assert result == []
    assert "not installed" in e.log_file.read_text()

def test_scope_out_host_not_forwarded(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"],
                          scope_in=["*.example.com"], scope_out=["admin.example.com"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t)
    captured = {}
    def fake_run(cmd, input=None, capture_output=None, text=None, timeout=None, **kwargs):
        tool = cmd[0]
        captured[tool] = input
        out = {
            "subfinder": "admin.example.com\ngood.example.com\n",
            "httpx": json.dumps({"url": "https://good.example.com", "status_code": 200}) + "\n",
            "nuclei": "",
        }[tool]
        return subprocess.CompletedProcess(cmd, 0, stdout=out, stderr="")
    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    orchestrator.run_pipeline(e, "recon")
    # subfinder discovered admin (excluded) + good; only good should be piped to httpx
    assert "admin.example.com" not in captured["httpx"]
    assert "good.example.com" in captured["httpx"]
    assert "scope-out" in e.log_file.read_text()


def test_run_streaming_emits_live_output_lines():
    import sys

    events: list[str] = []
    proc = orchestrator._run_streaming(
        [sys.executable, "-u", "-c", "print('a.example.com'); print('b.example.com')"],
        "",
        "subfinder",
        events.append,
    )
    assert proc.returncode == 0
    assert "a.example.com\nb.example.com\n" == proc.stdout
    assert any("[subfinder] a.example.com" in ev for ev in events)
    assert any("[subfinder] b.example.com" in ev for ev in events)


def test_run_pipeline_per_target_flag_fans_out(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["a.example.com", "b.example.com"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t if t == "subfinder" else None)
    monkeypatch.setattr(
        orchestrator,
        "load_pipeline",
        lambda _name: {
            "name": "fanout",
            "steps": [
                {
                    "tool": "subfinder",
                    "args": ["-silent"],
                    "input": "targets",
                    "output": "raw/subfinder.txt",
                    "parser": "subfinder",
                    "per_target_flag": "-d",
                    "workers": 2,
                }
            ],
        },
    )
    seen_cmds: list[list[str]] = []

    def fake_run(cmd, input=None, **kwargs):
        seen_cmds.append(list(cmd))
        target = cmd[-1]
        return subprocess.CompletedProcess(cmd, 0, stdout=f"sub.{target}\n", stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    findings = orchestrator.run_pipeline(e, "fanout")
    assert sorted(c[-2:] for c in seen_cmds) == [["-d", "a.example.com"], ["-d", "b.example.com"]]
    assert sorted(f.target for f in findings) == ["sub.a.example.com", "sub.b.example.com"]


def test_list_pipelines_includes_web_enum():
    names = [p["name"] for p in orchestrator.list_pipelines()]
    assert {"recon", "full_recon", "web_enum", "dns_enum", "web_deep", "passive_urls", "tls_recon"} <= set(names)
    expanded = orchestrator._expand_args(["dir", "-w", "{wordlist}"])
    assert "{wordlist}" not in expanded[2]
    assert expanded[2].endswith(".txt")


def test_run_pipeline_per_target_suffix_wires_ffuf_fuzz_url(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["https://example.com/"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t if t == "ffuf" else None)
    seen_cmds: list[list[str]] = []

    def fake_run(cmd, input=None, **kwargs):
        seen_cmds.append(list(cmd))
        return subprocess.CompletedProcess(
            cmd,
            0,
            stdout=json.dumps({"results": [{"url": "https://example.com/robots.txt", "status": 200, "length": 12}]}),
            stderr="",
        )

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    findings = orchestrator.run_pipeline(e, "web_deep")
    assert seen_cmds and seen_cmds[0][-2:] == ["-u", "https://example.com/FUZZ"]
    assert any(f.source_tool == "ffuf" and f.target == "https://example.com/robots.txt" for f in findings)


def test_run_pipeline_stops_when_stop_event_set(tmp_path, monkeypatch):
    import threading

    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t)

    stop = threading.Event()
    called: list[str] = []

    def fake_run(cmd, input=None, **kwargs):
        called.append(cmd[0])
        stop.set()  # cancel after the first step finishes
        return subprocess.CompletedProcess(cmd, 0, stdout="a.example.com\n", stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    events: list[str] = []
    findings = orchestrator.run_pipeline(e, "recon", on_progress=events.append, stop_event=stop)
    assert called == ["subfinder"]
    assert len(findings) == 1
    assert any("cancelled" in ev.lower() for ev in events)


def test_pipeline_preflight_and_scan_diffing(tmp_path, monkeypatch):
    _root(tmp_path, monkeypatch)
    e = engagement.create("acme", targets=["example.com"])
    monkeypatch.setattr(orchestrator.shutil, "which", lambda t: "/usr/bin/" + t if t == "subfinder" else None)

    pre = orchestrator.pipeline_preflight("recon")
    assert [c["tool"] for c in pre] == ["subfinder", "httpx", "nuclei"]
    assert [c["installed"] for c in pre] == [True, False, False]

    outputs = iter(["a.example.com\n", "a.example.com\nb.example.com\n"])

    def fake_run(cmd, input=None, **kwargs):
        return subprocess.CompletedProcess(cmd, 0, stdout=next(outputs), stderr="")

    monkeypatch.setattr(orchestrator.subprocess, "run", fake_run)
    orchestrator.run_pipeline(e, "recon")
    orchestrator.run_pipeline(e, "recon")
    assert [r["new_findings"] for r in e.runs] == [1, 1]
