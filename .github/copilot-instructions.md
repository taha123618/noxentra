# GitHub Copilot Instructions — Noxentra

Refer to [AGENTS.md](../AGENTS.md) for the full project architecture, conventions, and security invariants.

- **Environment**: Python >=3.10 managed via `uv`. Run `./scripts/check.sh` to execute `ruff` and `pytest`.
- **Security**: Use list-form `subprocess` only (no `shell=True`, no `curl | bash`, no forced `sudo`). Wrap untrusted tool output in `<scan_data>` delimiters (`src/noxentra/skill.py`).
- **Catalog**: Add tools as YAML entries in `src/noxentra/catalog/*.yaml` using tags from `src/noxentra/tags.py`, then run `uv run python scripts/gen_catalog_owners.py`.
