import socket
import subprocess
import webbrowser
from typing import ClassVar

from rich.panel import Panel
from rich.prompt import Prompt
from rich.text import Text

from noxentra.core import Noxentra, NoxentraCollection, clear_screen, console


class PortScan(Noxentra):
    TITLE = "Port scanning"

    def __init__(self):
        super().__init__(installable=False)

    def run(self):
        clear_screen()
        console.print(Panel(Text(self.TITLE, justify="center"), style="bold magenta"))
        from noxentra.os_detect import priv_argv
        target = Prompt.ask("[bold magenta]Select a Target IP[/bold magenta]", default="", show_default=False)
        subprocess.run(priv_argv(["nmap", "-O", "-Pn", target]), check=False)


class Host2IP(Noxentra):
    TITLE = "Host to IP "

    def __init__(self):
        super().__init__(installable=False)

    def run(self):
        clear_screen()
        console.print(Panel(Text(self.TITLE, justify="center"), style="bold magenta"))
        host = Prompt.ask("Enter host name (e.g. www.google.com):-  ")
        ips = socket.gethostbyname(host)
        console.print(f"[bold magenta]{host} -> {ips}[/bold magenta]")








class IsItDown(Noxentra):
    TITLE = "IsItDown (Check Website Down/Up)"
    DESCRIPTION = "Check Website Is Online or Not"

    def __init__(self):
        super().__init__(
            [('Open', self.open)], installable=False, runnable=False)

    def open(self):
        console.print(Panel("Opening isitdownrightnow.com", style="bold magenta"))
        webbrowser.open_new_tab("https://www.isitdownrightnow.com/")






class Striker(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2023-06"
    TITLE = "Striker"
    DESCRIPTION = "Recon & Vulnerability Scanning Suite"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/s0md3v/Striker.git",
        "cd Striker && pip3 install -r requirements.txt"
    ]
    PROJECT_URL = "https://github.com/s0md3v/Striker"

    def run(self):
        from noxentra.config import get_tools_dir
        site = Prompt.ask("Enter Site Name (example.com)")
        # Bug 3 fix: os.chdir() corrupts the process CWD permanently — use cwd= instead
        subprocess.run(
            ["sudo", "python3", "striker.py", site],
            cwd=str(get_tools_dir() / "Striker"),
            check=False,
        )






class PortScannerRanger(Noxentra):
    TITLE = "Port Scanner - rang3r"
    DESCRIPTION = "rang3r is a python script which scans in multi thread\n " \
                  "all alive hosts within your range that you specify."
    INSTALL_COMMANDS: ClassVar = [
        ("git clone https://github.com/floriankunushevci/rang3r.git;"
         "pip install --user termcolor")
    ]
    PROJECT_URL = "https://github.com/floriankunushevci/rang3r"

    def run(self):
        from noxentra.config import get_tools_dir
        ip = Prompt.ask("Enter IP")
        # Bug 3 fix: os.chdir() replaced with cwd= parameter
        subprocess.run(
            ["sudo", "python3", "rang3r.py", "--ip", ip],
            cwd=str(get_tools_dir() / "rang3r"),
            check=False,
        )


class Breacher(Noxentra):
    TITLE = "Breacher"
    DESCRIPTION = "An advanced multithreaded admin panel finder written in python."
    INSTALL_COMMANDS: ClassVar = ["git clone https://github.com/s0md3v/Breacher.git"]
    PROJECT_URL = "https://github.com/s0md3v/Breacher"

    def run(self):
        from noxentra.config import get_tools_dir
        domain = Prompt.ask("Enter domain (example.com)")
        # Bug 3 fix: os.chdir() replaced with cwd= parameter
        subprocess.run(
            ["python3", "breacher.py", "-u", domain],
            cwd=str(get_tools_dir() / "Breacher"),
            check=False,
        )
























class InformationGatheringTools(NoxentraCollection):
    TITLE = "Information gathering tools"
    TOOLS: ClassVar = [
        PortScan(),
        Host2IP(),
        IsItDown(),
        Striker(),
        PortScannerRanger(),
        Breacher(),
    ]

if __name__ == "__main__":
    tools = InformationGatheringTools()
    tools.show_options()
