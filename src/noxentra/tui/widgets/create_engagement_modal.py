"""Modal dialog for creating a new engagement with name, targets, and optional scope."""
from typing import ClassVar

from textual.app import ComposeResult
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen
from textual.widgets import Button, Input, Static

from noxentra import engagement


def _split_csv(raw: str) -> list[str]:
    return [part.strip() for part in raw.split(",") if part.strip()]


class CreateEngagementModal(ModalScreen[dict | None]):
    """Collects engagement name, targets, and optional scope-in / scope-out filters."""

    BINDINGS: ClassVar = [("escape", "cancel", "Cancel")]

    def compose(self) -> ComposeResult:
        with Vertical(id="engage-create-box"):
            yield Static("● New Engagement", id="eng-modal-title")
            yield Input(placeholder="name (e.g. acme-q4)", id="eng-name")
            yield Input(placeholder="targets comma-separated (e.g. example.com, 10.0.0.1)", id="eng-targets")
            yield Input(placeholder="optional scope-in globs (defaults to targets)", id="eng-scope-in")
            yield Input(placeholder="optional scope-out exclusions (e.g. admin.example.com)", id="eng-scope-out")
            yield Static("", id="eng-error")
            with Horizontal(id="eng-modal-actions"):
                yield Button("Create", variant="primary", id="eng-submit")
                yield Button("Cancel", id="eng-cancel")

    def on_mount(self) -> None:
        self.query_one("#eng-name", Input).focus()

    def _try_submit(self) -> None:
        name = self.query_one("#eng-name", Input).value.strip()
        targets = _split_csv(self.query_one("#eng-targets", Input).value)
        scope_in_raw = self.query_one("#eng-scope-in", Input).value.strip()
        scope_out = _split_csv(self.query_one("#eng-scope-out", Input).value)
        err = self.query_one("#eng-error", Static)
        try:
            engagement._validate_name(name)
        except ValueError:
            err.update("✘ Invalid engagement name (use letters/digits, no '/' or '..').")
            self.query_one("#eng-name", Input).focus()
            return
        if not targets:
            err.update("✘ Enter at least one target.")
            self.query_one("#eng-targets", Input).focus()
            return
        scope_in = _split_csv(scope_in_raw) if scope_in_raw else None
        self.dismiss({
            "name": name,
            "targets": targets,
            "scope_in": scope_in,
            "scope_out": scope_out,
        })

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "eng-submit":
            self._try_submit()
        else:
            self.dismiss(None)

    def on_input_submitted(self, event: Input.Submitted) -> None:
        if event.input.id == "eng-name":
            self.query_one("#eng-targets", Input).focus()
        elif event.input.id == "eng-targets":
            self.query_one("#eng-scope-in", Input).focus()
        elif event.input.id == "eng-scope-in":
            self.query_one("#eng-scope-out", Input).focus()
        else:
            self._try_submit()

    def action_cancel(self) -> None:
        self.dismiss(None)
