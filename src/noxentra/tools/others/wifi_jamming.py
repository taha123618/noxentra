from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection


class WifiJammerNG(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo deleted (404)"
    TITLE = "WifiJammer-NG"
    DESCRIPTION = "Continuously jam all wifi clients and access points within range."
    SUPPORTED_OS: ClassVar = ["linux"]
    REQUIRES_WIFI = True
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/MisterBianco/wifijammer-ng.git",
        "cd wifijammer-ng;pip install --user -r requirements.txt"
    ]
    RUN_COMMANDS: ClassVar = [
        "cd wifijammer-ng && sudo python3 wifijammer.py --help",
    ]
    PROJECT_URL = "https://github.com/MisterBianco/wifijammer-ng"


class KawaiiDeauther(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo archived by author (last commit 2020-02)"
    TITLE = "KawaiiDeauther"
    DESCRIPTION = "Kawaii Deauther is a pentest toolkit whose goal is to perform \n " \
                  "jam on WiFi clients/routers and spam many fake AP for testing purposes."
    SUPPORTED_OS: ClassVar = ["linux"]
    REQUIRES_WIFI = True
    INSTALL_COMMANDS: ClassVar = [
        "git clone https://github.com/aryanrtm/KawaiiDeauther.git",
        "cd KawaiiDeauther;sudo bash install.sh"
    ]
    RUN_COMMANDS: ClassVar = ["cd KawaiiDeauther;sudo bash KawaiiDeauther.sh"]
    PROJECT_URL = "https://github.com/aryanrtm/KawaiiDeauther"


class WifiJammingTools(NoxentraCollection):
    TITLE = "Wifi Deauthenticate"
    TOOLS: ClassVar = [
        WifiJammerNG(),
        KawaiiDeauther()
    ]

if __name__ == "__main__":
    tools = WifiJammingTools()
    tools.show_options()
