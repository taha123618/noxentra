from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection, console


class AnonymouslySurf(Noxentra):
    TITLE = "Anonymously Surf"
    DESCRIPTION = (
        "It automatically overwrites the RAM when the system shuts down\n"
        "and also changes your IP address."
    )
    # Bug 28 fix: was "cd kali-anonsurf && ./installer.sh && cd .. && sudo rm -r kali-anonsurf"
    # Deleting the source on install means there is no retry if install fails.
    # Now kept in a separate step so failure does not destroy the source.
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/Und3rf10w/kali-anonsurf.git",
        "cd kali-anonsurf && sudo ./installer.sh",
    ]
    RUN_COMMANDS: ClassVar = ["sudo anonsurf start"]
    PROJECT_URL = "https://github.com/Und3rf10w/kali-anonsurf"
    SUPPORTED_OS: ClassVar = ["linux"]

    def __init__(self):
        super().__init__([("Stop", self.stop)])

    def stop(self):
        import subprocess

        from noxentra.os_detect import priv_argv
        console.print("[bold magenta]Stopping Anonsurf...[/bold magenta]")
        subprocess.run(priv_argv(["anonsurf", "stop"]), check=False)


class AnonSurfTools(NoxentraCollection):
    TITLE = "Anonymously Hiding Tools"
    TOOLS: ClassVar = [
        AnonymouslySurf(),
    ]


if __name__ == "__main__":
    tools = AnonSurfTools()
    tools.show_options()
