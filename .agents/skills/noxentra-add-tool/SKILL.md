---
name: noxentra-add-tool
description: Add or update a security tool in Noxentra's YAML catalog or Python tool classes, validate taxonomy tags, regenerate catalog owners, and verify conformance. Use when adding, archiving, or editing tools in src/noxentra/catalog/ or src/noxentra/tools/.
---

# Add or Update a Noxentra Tool

## Steps

1. **Choose the target**:
   - Prefer adding a YAML entry in the matching `src/noxentra/catalog/<category>.yaml`.
   - Only add a `Noxentra` subclass in `src/noxentra/tools/` if the tool requires custom Python install/run/menu logic.
2. **Author the entry**:
   - Set `title`, `description`, `project_url`, `tags`, and safe `install_commands` / `run_commands` (no `curl | bash`, no forced `sudo`).
   - Pick tags exclusively from `TAXONOMY` in `src/noxentra/tags.py`.
3. **Regenerate catalog owners**:
   - Run `uv run python scripts/gen_catalog_owners.py` so `src/noxentra/catalog_owners.py` includes any new GitHub owner.
4. **Verify**:
   - Run `uv run --group dev pytest tests/test_registry.py tests/test_discover.py -q` and `uv run ruff check . --select=E9,F63,F7,F82,PLE,YTT`.
   - Done when all registry, taxonomy, and owner-freshness tests pass.
