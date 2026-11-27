import subprocess
from typing import ClassVar

from rich.prompt import Prompt

from noxentra.core import Noxentra, NoxentraCollection


class DDoSTool(Noxentra):
    TITLE = "DDoS"
    SUPPORTED_OS: ClassVar = ["linux"]
    DESCRIPTION = (
        "Best DDoS Attack Script With 36 Plus Methods. "
        "DDoS attacks for SECURITY TESTING PURPOSES ONLY!"
    )
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/the-deepnet/ddos.git",
        "cd ddos && sudo pip3 install -r requirements.txt",
    ]
    PROJECT_URL = "https://github.com/the-deepnet/ddos"

    def run(self):
        from noxentra.config import get_tools_dir
        method     = Prompt.ask("Enter Method")
        url        = Prompt.ask("Enter URL")
        threads    = Prompt.ask("Enter Threads")
        proxylist  = Prompt.ask("Enter ProxyList")
        multiple   = Prompt.ask("Enter Multiple")
        timer      = Prompt.ask("Enter Timer")
        # Bug 4 fix: removed os.system("cd ddos;") — use cwd= instead
        subprocess.run(
            ["sudo", "python3", "ddos.py", method, url,
             "socks_type5.4.1", threads, proxylist, multiple, timer],
            cwd=str(get_tools_dir() / "ddos"),
            check=False,
        )


class SlowLoris(Noxentra):
    TITLE = "SlowLoris"
    SUPPORTED_OS: ClassVar = ["linux"]
    DESCRIPTION = (
        "Slowloris is basically an HTTP Denial of Service attack. "
        "It sends lots of HTTP requests."
    )
    INSTALL_COMMANDS: ClassVar = ["sudo pip3 install slowloris"]

    def run(self):
        target_site = Prompt.ask("Enter Target Site")
        subprocess.run(["slowloris", target_site], check=False)


class Asyncrone(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo deleted (404)"
    TITLE = "Asyncrone | Multifunction SYN Flood DDoS Weapon"
    SUPPORTED_OS: ClassVar = ["linux"]
    DESCRIPTION = (
        "aSYNcrone is a C language based, multifunction SYN Flood DDoS Weapon.\n"
        "Disable the destination system by sending SYN packets intensively."
    )
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/fatih4842/aSYNcrone.git",
        "cd aSYNcrone && sudo gcc aSYNcrone.c -o aSYNcrone -lpthread",
    ]
    PROJECT_URL = "https://github.com/fatihsnsy/aSYNcrone"

    def run(self):
        from noxentra.config import get_tools_dir
        source_port = Prompt.ask("Enter Source Port")
        target_ip   = Prompt.ask("Enter Target IP")
        target_port = Prompt.ask("Enter Target Port")
        # Bug 5 fix: 1000 was int — subprocess requires all args str
        # Bug 4 fix: removed os.system("cd aSYNcrone;") — use cwd= instead
        subprocess.run(
            ["sudo", "./aSYNcrone", str(source_port), str(target_ip), str(target_port), "1000"],
            cwd=str(get_tools_dir() / "aSYNcrone"),
            check=False,
        )


class GoldenEye(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo archived by author (last commit 2023-11)"
    TITLE = "GoldenEye"
    SUPPORTED_OS: ClassVar = ["linux"]
    DESCRIPTION = (
        "GoldenEye is a python3 app for SECURITY TESTING PURPOSES ONLY!\n"
        "GoldenEye is a HTTP DoS Test Tool.\n"
        "Usage: ./goldeneye.py <url> [OPTIONS]"
    )
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/jseidl/GoldenEye.git",
        "chmod -R 755 GoldenEye",
    ]
    PROJECT_URL = "https://github.com/jseidl/GoldenEye"

    def run(self):
        from noxentra.config import get_tools_dir
        # Bug 4 fix: removed os.system("cd GoldenEye; ...") — no-op cd subshell
        url = Prompt.ask("Enter target URL")
        subprocess.run(["sudo", "./goldeneye.py", url],
                       cwd=str(get_tools_dir() / "GoldenEye"), check=False)


class Saphyra(Noxentra):
    TITLE = "SaphyraDDoS"
    SUPPORTED_OS: ClassVar = ["linux"]
    DESCRIPTION = "A Python DDoS script for SECURITY TESTING PURPOSES ONLY."
    INSTALL_COMMANDS: ClassVar = [
        # Bug 7 fix: removed "sudo su" (first step was dropping into interactive root shell)
        "git clone https://github.com/anonymous24x7/Saphyra-DDoS.git",
        "chmod +x Saphyra-DDoS/saphyra.py",
    ]
    PROJECT_URL = "https://github.com/anonymous24x7/Saphyra-DDoS"

    def run(self):
        from noxentra.config import get_tools_dir
        url = Prompt.ask("Enter URL")
        # Vuln 1 fix: was os.system("python saphyra.py " + url) — command injection
        # Now uses subprocess list form — url is never interpolated into a shell string
        subprocess.run(
            ["python3", "saphyra.py", url],
            cwd=str(get_tools_dir() / "Saphyra-DDoS"),
            check=False,
        )


class DDOSTools(NoxentraCollection):
    TITLE = "DDOS Attack Tools"
    TOOLS: ClassVar = [DDoSTool(), SlowLoris(), Asyncrone(), GoldenEye(), Saphyra()]


if __name__ == "__main__":
    tools = DDOSTools()
    tools.show_options()
