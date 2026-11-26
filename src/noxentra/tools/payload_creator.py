import subprocess

from noxentra.core import Noxentra, NoxentraCollection, console


class TheFatRat(Noxentra):
    TITLE = "The FatRat"
    SUPPORTED_OS = ["linux"]
    DESCRIPTION = (
        "TheFatRat provides an easy way to create backdoors and payloads "
        "which can bypass most anti-virus."
    )
    INSTALL_COMMANDS = [
        "git clone https://github.com/Screetsec/TheFatRat.git",
        "cd TheFatRat && chmod +x setup.sh",
    ]
    RUN_COMMANDS = ["cd TheFatRat && sudo bash setup.sh"]
    PROJECT_URL = "https://github.com/Screetsec/TheFatRat"

    def __init__(self):
        super().__init__([
            ("Update", self.update),
            ("Troubleshoot", self.troubleshoot),
        ])

    def update(self):
        from noxentra.config import get_tools_dir
        cwd = str(get_tools_dir() / "TheFatRat")
        subprocess.run(["bash", "update"], cwd=cwd)
        subprocess.run(["chmod", "+x", "setup.sh"], cwd=cwd)
        subprocess.run(["bash", "setup.sh"], cwd=cwd)

    def troubleshoot(self):
        from noxentra.config import get_tools_dir
        cwd = str(get_tools_dir() / "TheFatRat")
        subprocess.run(["chmod", "+x", "chk_tools"], cwd=cwd)
        subprocess.run(["./chk_tools"], cwd=cwd)


class Brutal(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2020-03"
    TITLE = "Brutal"
    SUPPORTED_OS = ["linux"]
    DESCRIPTION = (
        "Brutal is a toolkit to quickly create various payloads, powershell attacks, "
        "virus attacks and launch listener for a Human Interface Device."
    )
    INSTALL_COMMANDS = [
        "git clone https://github.com/Screetsec/Brutal.git",
        "cd Brutal && chmod +x Brutal.sh",
    ]
    RUN_COMMANDS = ["cd Brutal && sudo bash Brutal.sh"]
    PROJECT_URL = "https://github.com/Screetsec/Brutal"

    def show_info(self):
        super().show_info()
        console.print(
            "[bold cyan]Requirements:[/bold cyan]\n"
            "  - Arduino Software (v1.6.7+)\n"
            "  - TeensyDuino\n"
            "  - Linux udev rules\n"
            "  See: https://github.com/Screetsec/Brutal/wiki/Install-Requirements"
        )


class PayloadCreatorTools(NoxentraCollection):
    TITLE = "Payload creation tools"
    # Bug 11 fix: show_options() override was missing `parent` parameter entirely —
    # the whole override is now deleted and the base class method is used instead.
    TOOLS = [
        TheFatRat(),
        Brutal(),
    ]


if __name__ == "__main__":
    tools = PayloadCreatorTools()
    tools.show_options()
