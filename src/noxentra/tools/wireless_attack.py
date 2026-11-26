from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection, console


class pixiewps(Noxentra):
    TITLE = "pixiewps"
    DESCRIPTION = (
        "Pixiewps is a tool written in C used to bruteforce offline the WPS pin\n"
        "exploiting the low or non-existing entropy of some Access Points "
        "(pixie dust attack)."
    )
    INSTALL_COMMANDS: ClassVar = [
        # Bug 29 fix: removed wget https://pastebin.com/... (insecure download from pastebin)
        "git clone https://github.com/wiire/pixiewps.git && apt-get -y install build-essential",
        "cd pixiewps && make",
        "cd pixiewps && sudo make install",
    ]
    PROJECT_URL = "https://github.com/wiire/pixiewps"
    SUPPORTED_OS: ClassVar = ["linux"]
    REQUIRES_WIFI = True

    def run(self):
        console.print(
            "[bold cyan]Usage:[/bold cyan]\n"
            " 1. Put interface into monitor mode: [yellow]airmon-ng start <iface>[/yellow]\n"
            " 2. Scan: [yellow]wash -i <mon-iface>[/yellow]\n"
            " 3. Attack: [yellow]reaver -i <mon-iface> -b <BSSID> -c <ch> -vvv -K 1 -f[/yellow]\n"
            " 4. Run: [yellow]pixiewps -h[/yellow]"
        )
























class WirelessAttackTools(NoxentraCollection):
    TITLE = "Wireless attack tools"
    TOOLS: ClassVar = [
        pixiewps(),
    ]


if __name__ == "__main__":
    tools = WirelessAttackTools()
    tools.show_options()
