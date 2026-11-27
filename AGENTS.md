# Noxentra — Agent Guidelines

Noxentra (`src/noxentra/`) is a Python >=3.10 CLI/TUI security & reconnaissance framework (`uv`-managed, `pyproject.toml`).

## Commands

- **Run full gate** (ruff + pytest + catalog/taxonomy conformance): `./scripts/check.sh` (or `make check`)
- **Run tests**: `uv run --group dev pytest -q`
- **Run CLI / TUI**: `uv run noxentra` (TUI) or `uv run noxentra --classic` (REPL)
- **Regenerate catalog owners** (required after adding/editing GitHub URLs in `src/noxentra/`): `uv run python scripts/gen_catalog_owners.py`

## Architecture

- **Entry & UI**: `cli.py` (classic REPL + headless flags) and `tui/` (`NoxentraApp` Textual TUI, `app.tcss`, screens, widgets).
- **Catalog & Tools**: `toolbox.py` owns `all_tools`, `tool_definitions`, and `RECOMMENDATIONS`; YAML-first entries in `src/noxentra/catalog/*.yaml` loaded by `registry.py` (`CatalogTool`) merge with legacy Python classes in `src/noxentra/tools/*.py`. Tags must come from `TAXONOMY` in `src/noxentra/tags.py`.
- **AI Layer**: `ai_recommend.py`, `ai_command.py`, `ai_goal.py`, `ai_summary.py`, `ai_report.py`, governed by `skill.py` and `skill/OPERATOR.md`.
- **Headless Orchestrator**: `orchestrator.py`, `engagement.py`, `findings.py` (20 normalized parsers + `diff_findings`), `report.py` (Markdown, HTML, SARIF v2.1.0), and `pipelines/*.yaml` (`recon`, `full_recon`, `web_enum`, `dns_enum`, `web_deep`, `passive_urls`, `tls_recon`, `cloud_scan`, `container_scan`, `iac_scan`, `k8s_scan`, `secret_scan`, `sast_scan`).

## Invariants

- **List-form `subprocess` only** — never pass `shell=True` or `curl | bash` install commands.
- **No forced `sudo`**, no hardcoded home paths (use `constants.USER_CONFIG_DIR`), secrets only in `~/.noxentra/.env` (mode 600).
- **AI grounding**: untrusted tool output goes inside `<scan_data>` delimiters (`skill.py`), never auto-execute AI-generated commands, and always provide a deterministic offline fallback.
- **Catalog owners**: whenever a GitHub URL in `src/noxentra/` changes, run `uv run python scripts/gen_catalog_owners.py` so `tests/test_discover.py::test_generated_owners_file_is_current` stays green.

## Project Skills (`.agents/skills/`)

- Adding or editing a tool in the catalog → `.agents/skills/noxentra-add-tool/SKILL.md`
- Editing Textual TUI screens, widgets, or `app.tcss` → `.agents/skills/noxentra-tui-dev/SKILL.md`
- Modifying AI modules (`ai_*.py`, `skill.py`) → `.agents/skills/noxentra-ai-feature/SKILL.md`
