import subprocess

from noxentra.core import Noxentra, NoxentraCollection


class Web2Attack(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2022-12"
    TITLE = "Web2Attack"
    DESCRIPTION = "Web hacking framework with tools, exploits by python"
    INSTALL_COMMANDS = [
        "git clone https://github.com/santatic/web2attack.git"
    ]
    RUN_COMMANDS = ["cd web2attack && sudo python3 w2aconsole"]
    PROJECT_URL = "https://github.com/santatic/web2attack"












class Dirb(Noxentra):
    TITLE = "Dirb"
    DESCRIPTION = (
        "DIRB is a Web Content Scanner. It looks for existing "
        "(and/or hidden) Web Objects.\n"
        "It basically works by launching a dictionary based "
        "attack against \n a web server and analyzing the response."
    )
    INSTALL_COMMANDS = [
        "git clone https://gitlab.com/kalilinux/packages/dirb.git",
        "cd dirb;sudo bash configure;make"
    ]
    PROJECT_URL = "https://gitlab.com/kalilinux/packages/dirb"

    def run(self):
        uinput = input("Enter Url >> ")
        subprocess.run(["sudo", "dirb", uinput], check=False)




























class WebAttackTools(NoxentraCollection):
    TITLE = "Web Attack tools"
    DESCRIPTION = ""
    TOOLS = [
        Web2Attack(),
        Dirb(),
    ]

if __name__ == "__main__":
    tools = WebAttackTools()
    tools.show_options()
