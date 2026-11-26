import subprocess

from noxentra.core import Noxentra, NoxentraCollection


class Apk2Gold(Noxentra):
    TITLE = "Apk2Gold"
    SUPPORTED_OS = ["linux"]
    DESCRIPTION = "Apk2Gold is a CLI tool for decompiling Android apps to Java"
    INSTALL_COMMANDS = [
        "git clone https://github.com/lxdvs/apk2gold.git",
        "cd apk2gold;sudo bash make.sh"
    ]
    PROJECT_URL = "https://github.com/lxdvs/apk2gold "

    def run(self):
        uinput = input("Enter (.apk) File >> ")
        subprocess.run(["sudo", "apk2gold", uinput], check=False)


class ReverseEngineeringTools(NoxentraCollection):
    TITLE = "Reverse engineering tools"
    TOOLS = [
        Apk2Gold(),
    ]

if __name__ == "__main__":
    tools = ReverseEngineeringTools()
    tools.show_options()
