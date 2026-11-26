"""Regression tests for security hardening fixes."""
import pytest

from noxentra import ai_recommend, config, engagement, orchestrator, os_detect
from noxentra.tools.phishing_attack import QRLJacking


def test_engagement_rejects_path_traversal(tmp_path, monkeypatch):
    monkeypatch.setattr(engagement, "ENGAGEMENTS_ROOT", tmp_path)
    for bad in ("", ".", "..", "../etc", "foo/bar", "foo\\bar"):
        with pytest.raises(ValueError):
            engagement.create(bad)
        with pytest.raises(ValueError):
            engagement.load(bad)


def test_ai_recommend_rejects_non_http_schemes(monkeypatch):
    monkeypatch.setattr(config, "ai_provider", lambda: "openai-compat")
    monkeypatch.setattr(config, "ai_base_url", lambda: "file:///etc/passwd")
    monkeypatch.setattr(config, "ai_key", lambda: "sk-test")

    assert ai_recommend.ask("hello") is None
    ok, msg = ai_recommend.test_connection()
    assert not ok
    assert "http://" in msg or "https://" in msg


def test_install_packages_uses_list_form_subprocess(monkeypatch):
    captured = {}

    def fake_run(argv, check=False):
        captured["argv"] = argv
        captured["check"] = check
        return type("Res", (), {"returncode": 0})()

    monkeypatch.setattr("subprocess.run", fake_run)
    info = os_detect.OSInfo(system="linux", pkg_manager="apt-get", is_root=True)
    assert os_detect.install_packages(["git", "curl;id"], os_info=info)
    assert isinstance(captured["argv"], list)
    assert captured["argv"] == ["apt-get", "install", "-y", "git", "curl;id"]


def test_qrljacking_uses_mktemp_not_static_tmp():
    joined = "\n".join(QRLJacking.INSTALL_COMMANDS)
    assert "/tmp/" not in joined
    assert "mktemp -d" in joined


def test_load_pipeline_rejects_path_traversal():
    for bad in ("", ".", "..", "../catalog/ddos", "a/b", "a\\b"):
        with pytest.raises(ValueError):
            orchestrator.load_pipeline(bad)
