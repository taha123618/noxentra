import noxentra.cli as noxentra
from noxentra.tags import TAXONOMY


def test_recommendation_tags_are_taxonomy_valid():
    # Every curated shortcut must map onto the one canonical vocabulary — guards
    # against typos like the old "port-scanner" (should be "port-scan").
    bad = {phrase: [t for t in tags if t not in TAXONOMY]
           for phrase, tags in noxentra._RECOMMENDATIONS.items()
           if any(t not in TAXONOMY for t in tags)}
    assert not bad, bad


def test_tag_index_speaks_one_vocabulary_from_real_tags():
    idx = noxentra._get_all_tags()
    # The whole index is taxonomy-valid (real tags + taxonomy-valid regex fallback).
    assert set(idx) <= set(TAXONOMY), sorted(set(idx) - set(TAXONOMY))
    # A tagged tool contributes exactly its real TAGS — no regex bleed.
    for tool, cat in noxentra._collect_all_tools():
        if getattr(tool, "TAGS", None):
            here = {tg for tg in idx if (tool, cat) in idx[tg]}
            assert here == set(tool.TAGS), (tool.TITLE, here, tool.TAGS)
            break


def test_legacy_overlay_titles_match_real_tools():
    # Overlays apply by exact title — a typo would silently no-op. Guard it.
    import yaml

    from noxentra import registry
    f = registry.CATALOG_DIR / "legacy_overlays.yaml"
    entries = (yaml.safe_load(f.read_text()) or {}).get("overlay", [])
    titles = {t.TITLE for t, _ in noxentra._collect_all_tools()}
    missing = [e["title"] for e in entries if e["title"] not in titles]
    assert not missing, missing
    assert len(entries) >= 90                       # the curated legacy batch landed


def test_free_text_routes_to_recommend(monkeypatch):
    # NL-first: a plain intent string goes to the AI1 free-text path.
    seen = {}
    monkeypatch.setattr(noxentra, "_recommend_freetext",
                        lambda intent: seen.setdefault("intent", intent))
    noxentra.recommend_tools("crack a wifi handshake")
    assert seen["intent"] == "crack a wifi handshake"


def test_arg_parser_flags():
    p = noxentra._build_arg_parser()
    ns = p.parse_args(["--engagement", "acme", "--targets", "example.com", "--ai-summary"])
    assert ns.engagement == "acme"
    assert ns.targets == "example.com"
    assert ns.pipeline is None        # default
    assert ns.ai_summary is True
    assert ns.report is False

def test_pipeline_runs_against_stored_targets(tmp_path, monkeypatch):
    from noxentra import engagement
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    engagement.create("acme", targets=["example.com"])  # targets already stored
    called = {}
    def fake_run(e, name):
        called["run"] = name
        return []
    monkeypatch.setattr(noxentra.orchestrator, "run_pipeline", fake_run)
    monkeypatch.setattr(noxentra.report, "generate_report", lambda e: e.report_file)
    args = noxentra._build_arg_parser().parse_args(["--engagement", "acme", "--pipeline", "recon"])
    noxentra._run_headless(args)
    assert called["run"] == "recon"   # ran with NO --targets

def test_load_targets_inline_vs_file(tmp_path):
    assert noxentra._load_targets("example.com") == ["example.com"]
    f = tmp_path / "t.txt"
    f.write_text("a.com\nb.com\n\n")
    assert noxentra._load_targets(str(f)) == ["a.com", "b.com"]

def test_run_headless_dispatches(tmp_path, monkeypatch):
    from noxentra import engagement
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    called = {}

    def fake_run(e, name):
        called["run"] = name
        return []
    monkeypatch.setattr(noxentra.orchestrator, "run_pipeline", fake_run)

    def fake_report(e):
        called["report"] = True
        return e.report_file
    monkeypatch.setattr(noxentra.report, "generate_report", fake_report)

    def fake_summary(e):
        called["summary"] = True
        return "ok"
    monkeypatch.setattr(noxentra.ai_summary, "summarize", fake_summary)

    args = noxentra._build_arg_parser().parse_args(
        ["--engagement", "acme", "--targets", "example.com", "--ai-summary"])
    noxentra._run_headless(args)

    assert called["run"] == "recon"
    assert called["report"] is True
    assert called["summary"] is True


def test_load_targets_comma_separated():
    assert noxentra._load_targets("75.2.60.5, https://devteampro.com/ , ") == [
        "75.2.60.5",
        "https://devteampro.com/",
    ]


def test_run_headless_merges_scope_out(tmp_path, monkeypatch):
    from noxentra import engagement

    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    engagement.create("acme", targets=["example.com"], scope_out=["legacy.example.com"])
    monkeypatch.setattr(noxentra.orchestrator, "run_pipeline", lambda _e, _n: [])
    monkeypatch.setattr(noxentra.report, "generate_report", lambda e: e.report_file)

    args = noxentra._build_arg_parser().parse_args([
        "--engagement", "acme",
        "--targets", "example.com,api.example.com",
        "--scope-out", "admin.example.com,legacy.example.com",
    ])
    noxentra._run_headless(args)
    saved = engagement.load("acme")
    assert saved is not None
    assert saved.targets == ["example.com", "api.example.com"]
    assert saved.scope_out == ["legacy.example.com", "admin.example.com"]


def test_list_pipelines_and_engagements_without_engagement(tmp_path, monkeypatch, capsys):
    import sys

    from noxentra import engagement

    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    engagement.create("acme", targets=["example.com"])
    monkeypatch.setattr(sys, "argv", ["noxentra", "--list-pipelines", "--list-engagements"])
    noxentra.main()
    out = capsys.readouterr().out
    assert "recon" in out
    assert "web_deep" in out
    assert "acme" in out
