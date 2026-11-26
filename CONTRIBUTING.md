# Contributing to Noxentra

Thank you for contributing to **Noxentra**!

## Development Setup

```bash
git clone https://github.com/taha123618/noxentra.git
cd noxentra
uv sync --group dev
```

Run the full check gate (lint + unit tests + catalog/taxonomy conformance) before opening a PR:

```bash
./scripts/check.sh
```

## Adding Tools to the Catalog

Most tools are declarative YAML entries in `src/noxentra/catalog/*.yaml`:

1. Add your entry under `tools:` using valid tags from `src/noxentra/tags.py`.
2. Include `usage:` examples and `lab_safe_notes` for authorized-testing guidance.
3. Regenerate catalog owners if you added or changed any GitHub URL:
   ```bash
   uv run python scripts/gen_catalog_owners.py
   ```
4. Verify everything passes with `./scripts/check.sh`.

## Security Guidelines

- Never use `shell=True` with user input or `curl | bash` install commands.
- Keep untrusted tool output inside `<scan_data>` delimiters (`src/noxentra/skill.py`).
- Report security vulnerabilities privately via [SECURITY.md](SECURITY.md).
