from textual.message import Message
from textual.widgets import OptionList
from textual.widgets.option_list import Option

# (command, help) — all commands are active in NoxentraApp.
# No /search: just type in the prompt to filter live.
COMMANDS = [
    ("/config", "edit settings"),
    ("/update", "check for & how to update noxentra"),
    ("/recommend", "AI tool recommendation"),
    ("/find", "discover tools on GitHub"),
    ("/goal", "AI goal planner"),
    ("/tags", "browse tools by tag"),
    ("/skill", "operator playbook & charter"),
    ("/report", "export findings"),
    ("/menu", "browse categories"),
    ("/quit", "exit noxentra"),
]


class CommandPalette(OptionList):
    """Floating slash-command palette, filtered by the bottom prompt. (claude-slash-menu)"""

    class Selected(Message):
        def __init__(self, command: str) -> None:
            self.command = command
            super().__init__()

    def __init__(self):
        super().__init__(*self._opts(""))
        self.can_focus = False      # prompt keeps focus; ↑↓ are routed here from it

    def on_mount(self) -> None:
        if self.option_count and self.highlighted is None:
            self.highlighted = 0

    def _opts(self, needle: str) -> list[Option]:
        n = needle.lower()
        return [
            Option(f"{cmd}  {help_}", id=cmd)
            for cmd, help_ in COMMANDS
            if not n or n in cmd.lower() or n in help_.lower()
        ]

    def filter(self, needle: str) -> None:
        self.clear_options()
        self.add_options(self._opts(needle))
        if self.option_count:
            self.highlighted = 0

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:  # mouse click
        event.stop()
        self.post_message(self.Selected(event.option.id))
