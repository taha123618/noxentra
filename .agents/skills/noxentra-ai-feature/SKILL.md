---
name: noxentra-ai-feature
description: Extend or debug Noxentra's AI layer (ai_recommend, ai_command, ai_goal, ai_summary, ai_report, skill.py). Use when editing AI prompts, transport, grounding, or offline fallbacks.
---

# Noxentra AI Feature Development

## Grounding & Safety Rules

- **Opt-in only**: AI calls use `NOXENTRA_AI_*` / `~/.noxentra/.env` or local Ollama; every feature must degrade to a deterministic offline fallback when no model is reachable.
- **No auto-execution**: AI-suggested commands (`ai_command.py`, `ai_goal.py`) require explicit user confirmation and run via list-form `subprocess` only.
- **Untrusted data framing**: Wrap any tool output, repo metadata, or scan findings passed to a model in `<scan_data>` delimiters via `src/noxentra/skill.py` (`OPERATOR.md` charter).
- **No fabricated facts**: `ai_summary.py` and `ai_report.py` may only summarize deterministic findings present in `findings.json`.

## Verification

- Run `uv run --group dev pytest tests/test_ai_command.py tests/test_ai_goal.py tests/test_ai_recommend.py tests/test_ai_report.py tests/test_ai_summary.py tests/test_skill.py -q`.
- Done when all AI and grounding guardrail tests pass.
