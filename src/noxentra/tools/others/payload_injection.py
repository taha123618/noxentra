from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection


class DebInject(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo archived by author (last commit 2022-04)"
    TITLE = "Debinject"
    DESCRIPTION = "Debinject is a tool that inject malicious code into *.debs"
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/UndeadSec/Debinject.git"]
    RUN_COMMANDS: ClassVar = ["cd Debinject;python debinject.py"]
    PROJECT_URL = "https://github.com/UndeadSec/Debinject"


class Pixload(Noxentra):
    TITLE = "Pixload"
    DESCRIPTION = "Pixload -- Image Payload Creating tools \n " \
                  "Pixload is Set of tools for creating/injecting payload into images."
    INSTALL_COMMANDS: ClassVar = [
        "sudo apt install libgd-perl libimage-exiftool-perl libstring-crc32-perl",
        "git clone https://github.com/chinarulezzz/pixload.git"
    ]
    PROJECT_URL = "https://github.com/chinarulezzz/pixload"

    def __init__(self):
        super().__init__(runnable = False)


class PayloadInjectorTools(NoxentraCollection):
    TITLE = "Payload Injector"
    TOOLS: ClassVar = [
        DebInject(),
        Pixload()
    ]

if __name__ == "__main__":
    tools = PayloadInjectorTools()
    tools.show_options()
