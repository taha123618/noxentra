"""Skill screen: read-only viewer for the operator playbook (OPERATOR.md)."""
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Static

from noxentra import skill
from noxentra.tui import glyphs
from noxentra.tui.screens.base import NoxentraScreen


class SkillScreen(NoxentraScreen):
    BINDINGS: ClassVar = [("escape", "app.pop_screen", "Back"), ("left", "app.pop_screen", "Back")]

    def content(self) -> ComposeResult:
        with VerticalScroll(id="skill-scroll"):
            yield Static(skill.playbook(), id="skill-body", markup=False)
        yield Static(f" {glyphs.PROMPT} ↑↓ scroll · ← esc back", id="nx-hint")

    def on_mount(self) -> None:
        pass
