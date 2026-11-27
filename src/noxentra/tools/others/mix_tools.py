from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection


class TerminalMultiplexer(Noxentra):
    TITLE = "Terminal Multiplexer"
    DESCRIPTION = (
        "Terminal Multiplexer (tilix) is a tiling terminal emulator that "
        "allows opening several terminal sessions inside one window."
    )
    # Bug 19 fix: tilix is a Debian/Ubuntu package only — mark Linux-only
    INSTALL_COMMANDS: ClassVar = ["sudo apt-get install -y tilix"]
    SUPPORTED_OS: ClassVar = ["linux"]

    def __init__(self):
        # Py3-4 fix: super(TerminalMultiplexer, self) → super()
        super().__init__(runnable=False)


class Crivo(Noxentra):
    TITLE = "Crivo"
    DESCRIPTION = (
        "A tool for extracting and filtering URLs, IPs, domains, and subdomains\n"
        "from web pages or text, with built-in web scraping capabilities.\n"
        "See: python3 crivo_cli.py -h"
    )
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/GMDSantana/crivo.git",
        # Bug 18 verify: this is correct — cd and pip in same string works
        "cd crivo && pip install --user -r requirements.txt",
    ]
    PROJECT_URL = "https://github.com/GMDSantana/crivo"

    def __init__(self):
        # Py3-4 fix: super(Crivo, self) → super()
        super().__init__(runnable=False)


class MixTools(NoxentraCollection):
    TITLE = "Mix tools"
    TOOLS: ClassVar = [
        TerminalMultiplexer(),
        Crivo()
    ]

if __name__ == "__main__":
    tools = MixTools()
    tools.show_options()
