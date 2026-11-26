from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection


class KnockMail(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Unmaintained — no commits since 2021-12"
    TITLE = "Knockmail"
    DESCRIPTION = "KnockMail Tool Verify If Email Exists"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/heywoodlh/KnockMail.git",
        "cd KnockMail;sudo pip3 install -r requirements.txt"
    ]
    RUN_COMMANDS: ClassVar = ["cd KnockMail;python3 knockmail.py"]
    PROJECT_URL = "https://github.com/heywoodlh/KnockMail"


class EmailVerifyTools(NoxentraCollection):
    TITLE = "Email Verify tools"
    TOOLS: ClassVar = [KnockMail()]

if __name__ == "__main__":
    tools = EmailVerifyTools()
    tools.show_options()
