import subprocess
from typing import ClassVar

from rich.prompt import Prompt

from noxentra.core import Noxentra, NoxentraCollection, console


class FacialFind(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2022-02"
    TITLE = "Find SocialMedia By Facial Recognation System"
    DESCRIPTION = "A Social Media Mapping Tool that correlates profiles\n " \
                  "via facial recognition across different sites."
    INSTALL_COMMANDS: ClassVar = [
        "sudo apt install -y software-properties-common",
        "sudo add-apt-repository ppa:mozillateam/firefox-next && sudo apt update && sudo apt upgrade",
        "git clone https://github.com/Greenwolf/social_mapper.git",
        "sudo apt install -y build-essential cmake libgtk-3-dev libboost-all-dev",
        "cd social_mapper/setup",
        "sudo python3 -m pip install --no-cache-dir -r requirements.txt",
        ('echo "[!]Now You have To do some Manually\n'
         '[!] Install the Geckodriver for your operating system\n'
         '[!] Copy & Paste Link And Download File As System Configuration\n'
         '[#] https://github.com/mozilla/geckodriver/releases\n'
         '[!!] On Linux you can place it in /usr/bin "| boxes | lolcat')
    ]
    PROJECT_URL = "https://github.com/Greenwolf/social_mapper"

    def run(self):
        import subprocess

        from noxentra.config import get_tools_dir
        setup_dir = get_tools_dir() / "social_mapper" / "setup"
        subprocess.run(["python3", "social_mapper.py", "-h"], cwd=str(setup_dir), check=False)
        console.print(
            "[bold magenta]Set username and password in social_mapper.py before running.[/]\n"
            "[magenta]Usage: python social_mapper.py -f <folder> -i <path> -m fast <AcName> -fb -tw[/]"
        )


class FindUser(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo deleted (404)"
    TITLE = "Find SocialMedia By UserName"
    DESCRIPTION = "Find usernames across over 75 social networks"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/xHak9x/finduser.git",
        "cd finduser && sudo chmod +x finduser.sh"
    ]
    RUN_COMMANDS: ClassVar = ["cd finduser && sudo bash finduser.sh"]
    PROJECT_URL = "https://github.com/xHak9x/finduser"


class Sherlock(Noxentra):
    TITLE = "Sherlock"
    DESCRIPTION = "Hunt down social media accounts by username across social networks \n " \
                  "For More Usage \n" \
                  "\t >>python3 sherlock --help"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/sherlock-project/sherlock.git",
        "cd sherlock;sudo python3 -m pip install -r requirements.txt"
    ]
    PROJECT_URL = "https://github.com/sherlock-project/sherlock"

    def run(self):
        from noxentra.config import get_tools_dir
        name = Prompt.ask("Enter Username")
        # Bug 3 fix: os.chdir() replaced with cwd= parameter
        subprocess.run(
            ["python3", "sherlock", name],
            cwd=str(get_tools_dir() / "sherlock"),
            check=False,
        )


class SocialScan(Noxentra):
    TITLE = "SocialScan | Username or Email"
    DESCRIPTION = "Check email address and username availability on online " \
                  "platforms with 100% accuracy"
    INSTALL_COMMANDS: ClassVar = ["pip install --user socialscan"]
    PROJECT_URL = "https://github.com/iojw/socialscan"

    def run(self):
        name = input(
            "Enter Username or Emailid (if both then please space between email & username) >> ")
        subprocess.run(["sudo", "socialscan", f"{name}"], check=False)


class SocialMediaFinderTools(NoxentraCollection):
    TITLE = "SocialMedia Finder"
    TOOLS: ClassVar = [
        FacialFind(),
        FindUser(),
        Sherlock(),
        SocialScan()
    ]

if __name__ == "__main__":
    tools = SocialMediaFinderTools()
    tools.show_options()
