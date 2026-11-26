
from noxentra.core import Noxentra, NoxentraCollection






















# Bug 10 fix: WifiPhisher removed from phishing tools — it belongs in wireless_attack.py








class QRLJacking(Noxentra):
    TITLE = "QRLJacking"
    DESCRIPTION = "QRLJacking — session hijacking attack vector targeting QR code based login"
    INSTALL_COMMANDS = [
        "git clone https://github.com/OWASP/QRLJacking.git",
        # Bug fix: geckodriver must be fetched as a binary, not cloned from source
        "GECKO_TMP=$(mktemp -d) && "
        "GECKO_VER=$(curl -s https://api.github.com/repos/mozilla/geckodriver/releases/latest | grep tag_name | cut -d '\"' -f4) && "
        "wget -q https://github.com/mozilla/geckodriver/releases/download/$GECKO_VER/geckodriver-$GECKO_VER-linux64.tar.gz -O \"$GECKO_TMP/geckodriver.tar.gz\" && "
        "tar -xzf \"$GECKO_TMP/geckodriver.tar.gz\" -C \"$GECKO_TMP\" && sudo mv \"$GECKO_TMP/geckodriver\" /usr/local/bin/ && rm -rf \"$GECKO_TMP\"",
        "cd QRLJacking && pip3 install --user -r QRLJacker/requirements.txt",
    ]
    RUN_COMMANDS = ["cd QRLJacking/QRLJacker && python3 QrlJacker.py"]
    PROJECT_URL = "https://github.com/OWASP/QRLJacking"




class BlackPhish(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo archived by author (last commit 2024-09)"
    TITLE = "BlackPhish"
    SUPPORTED_OS = ["linux"]
    INSTALL_COMMANDS = [
        "git clone https://github.com/iinc0gnit0/BlackPhish.git",
        "cd BlackPhish && sudo bash install.sh",
    ]
    RUN_COMMANDS = ["cd BlackPhish && sudo python3 blackphish.py"]
    PROJECT_URL = "https://github.com/iinc0gnit0/BlackPhish"

    def __init__(self):
        # Bug fix: super() Python 3 style
        super().__init__([("Update", self.update)])

    def update(self):
        import subprocess

        from noxentra.config import get_tools_dir
        subprocess.run(["bash", "update.sh"], cwd=str(get_tools_dir() / "BlackPhish"))




class PhishingAttackTools(NoxentraCollection):
    TITLE = "Phishing attack tools"
    TOOLS = [
        QRLJacking(),
        BlackPhish(),
    ]


if __name__ == "__main__":
    tools = PhishingAttackTools()
    tools.show_options()
