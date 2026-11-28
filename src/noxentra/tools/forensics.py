from typing import ClassVar

from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from noxentra.core import Noxentra, NoxentraCollection, console


class BulkExtractor(Noxentra):
    TITLE = "Bulk extractor"
    DESCRIPTION = "Extract useful information without parsing the file system"
    PROJECT_URL = "https://github.com/simsong/bulk_extractor"
    SUPPORTED_OS: ClassVar = ["linux"]

    def __init__(self):
        super().__init__([
            ('GUI Mode (Download required)', self.gui_mode),
            ('CLI Mode', self.cli_mode)
        ], installable=False, runnable=False)

    def gui_mode(self):
        import subprocess

        from noxentra.config import get_tools_dir
        console.print(Panel(Text(self.TITLE, justify="center"), style="bold magenta"))
        console.print("[bold magenta]Cloning repository and attempting to run GUI...[/]")
        tools_dir = get_tools_dir()
        subprocess.run(["git", "clone", "https://github.com/simsong/bulk_extractor.git"],
                       cwd=str(tools_dir), check=False)
        be_dir = tools_dir / "bulk_extractor"
        subprocess.run(["./BEViewer"], cwd=str(be_dir / "java_gui"), check=False)
        console.print(
            "[magenta]If you get an error after clone go to /java_gui/src/ and compile the .jar file && run ./BEViewer[/]")
        console.print(
            "[magenta]Please visit for more details about installation: https://github.com/simsong/bulk_extractor[/]")

    def cli_mode(self):
        import subprocess

        from noxentra.os_detect import priv_argv
        console.print(Panel(Text(self.TITLE + " - CLI Mode", justify="center"), style="bold magenta"))
        subprocess.run(priv_argv(["apt", "install", "-y", "bulk-extractor"]), check=False)
        console.print("[magenta]bulk_extractor [options] imagefile[/]")
        subprocess.run(["bulk_extractor", "-h"], check=False)


class Volatility3(Noxentra):
    TITLE = "Volatility 3 (Memory Forensics)"
    DESCRIPTION = (
        "The world's most widely used memory forensics framework.\n"
        "Usage: python3 vol.py -f memory.dmp windows.pslist"
    )
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/volatilityfoundation/volatility3.git",
        "cd volatility3 && pip install --user -r requirements.txt",
    ]
    PROJECT_URL = "https://github.com/volatilityfoundation/volatility3"

    def run(self):
        import subprocess

        from noxentra.config import get_tools_dir
        dump = Prompt.ask("Enter path to memory dump")
        plugin = Prompt.ask("Enter plugin", default="windows.pslist")
        subprocess.run(
            ["python3", "vol.py", "-f", dump, plugin],
            cwd=str(get_tools_dir() / "volatility3"),
            check=False,
        )


class ForensicTools(NoxentraCollection):
    TITLE = "Forensic tools"
    TOOLS: ClassVar = [
        BulkExtractor(),
        Volatility3(),
    ]

if __name__ == "__main__":
    tools = ForensicTools()
    tools.show_options()
