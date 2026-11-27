---
name: noxentra-tui-dev
description: Build, style, or debug Noxentra's Textual TUI screens, widgets, and keybindings in src/noxentra/tui/. Use when modifying app.py, app.tcss, screens/, widgets/, or TUI tests.
---

# Noxentra TUI Development

## Steps

1. **Inspect existing layout & style**:
   - Check `src/noxentra/tui/app.py` (`NoxentraApp`), `src/noxentra/tui/app.tcss`, and the target screen in `src/noxentra/tui/screens/` or widget in `src/noxentra/tui/widgets/`.
2. **Implement changes**:
   - Put visual styling in `src/noxentra/tui/app.tcss` (single source of TUI styles).
   - Keep `on_mount` non-blocking; offload network, `is_installed()` probing, or subprocess/pipeline execution to `@work(thread=True)` and stream live output to `LivePanel`.
   - Annotate mutable class defaults (`BINDINGS: ClassVar = [...]`) to satisfy `RUF012`.
   - Keep `CommandPalette` (`src/noxentra/tui/widgets/command_palette.py`) descriptions free of accidental command-prefix collisions.
3. **Test with Textual Pilot**:
   - Add or update async pilot tests using `NoxentraApp().run_test()` in `tests/test_tui_*.py`.
   - Run `uv run --group dev pytest tests/test_tui_*.py -q` and `uv run --group dev ruff check src/noxentra/tui tests/test_tui_*.py`.
   - Done when all targeted TUI tests and ruff checks pass.
