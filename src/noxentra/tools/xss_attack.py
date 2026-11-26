import subprocess
from typing import ClassVar

from rich.panel import Panel
from rich.prompt import Prompt

from noxentra.core import Noxentra, NoxentraCollection, console


class XSSFinder(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2019-08"
    TITLE = "Extended XSS Searcher and Finder"
    DESCRIPTION = "Extended XSS Searcher and Finder"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/Damian89/extended-xss-search.git"]
    PROJECT_URL = "https://github.com/Damian89/extended-xss-search"

    def after_install(self):
        console.print(Panel.fit(
            "[bold cyan]Follow These Steps After Installation:[/bold cyan]\n"
            "[red]*[/red] Go to [yellow]extended-xss-search[/yellow] directory\n"
            "[green]*[/green] Rename [bold]example.app-settings.conf[/bold] → [bold]app-settings.conf[/bold]",
            title="[ Install Notes ]",
            border_style="magenta"
        ))
        input("Press ENTER to continue")

    def run(self):
        console.print(Panel.fit(
            "[bold cyan]You need to add links to scan[/bold cyan]\n"
            "[red]*[/red] Go to [yellow]extended-xss-search/config/urls-to-test.txt[/yellow]\n"
            "[green]*[/green] Run: [bold]python3 extended-xss-search.py[/bold]",
            title="[ Run Instructions ]",
            border_style="blue"
        ))


class XSSCon(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2019-09"
    TITLE = "XSSCon"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/menkrep1337/XSSCon.git",
        "sudo chmod 755 -R XSSCon"
    ]
    PROJECT_URL = "https://github.com/menkrep1337/XSSCon"

    def run(self):
        console.print(Panel.fit(
            "Enter target website to scan with XSSCon:",
            title="[bold yellow]XSSCon[/bold yellow]",
            border_style="bright_yellow"
        ))
        website = Prompt.ask("[bold cyan]Enter Website[/bold cyan]")
        from noxentra.config import get_tools_dir
        subprocess.run(["python3", "xsscon.py", "-u", website],
                       cwd=str(get_tools_dir() / "XSSCon"), check=False)


class XanXSS(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2018-11"
    TITLE = "XanXSS"
    DESCRIPTION = "Reflected XSS searching tool that creates payloads from templates."
    INSTALL_COMMANDS: ClassVar = ["git clone https://github.com/Ekultek/XanXSS.git"]
    PROJECT_URL = "https://github.com/Ekultek/XanXSS"

    def run(self):
        from noxentra.config import get_tools_dir
        subprocess.run(["python3", "xanxss.py", "-h"],
                       cwd=str(get_tools_dir() / "XanXSS"), check=False)


class XSSAttackTools(NoxentraCollection):
    TITLE = "XSS Attack Tools"
    TOOLS: ClassVar = [
        XSSFinder(),
        XSSCon(),
        XanXSS(),
    ]

    def show_info(self):
        console.print(Panel.fit(
            "[bold magenta]XSS Attack Tools Collection[/bold magenta]\n"
            "A curated set of tools for XSS vulnerability analysis and exploitation.",
            border_style="bright_magenta"
        ))
