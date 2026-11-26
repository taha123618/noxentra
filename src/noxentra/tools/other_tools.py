import subprocess
from typing import ClassVar

from rich.prompt import Prompt

from noxentra.core import Noxentra, NoxentraCollection
from noxentra.tools.others.android_attack import AndroidAttackTools
from noxentra.tools.others.email_verifier import EmailVerifyTools
from noxentra.tools.others.hash_crack import HashCrackingTools
from noxentra.tools.others.homograph_attacks import IDNHomographAttackTools
from noxentra.tools.others.mix_tools import MixTools
from noxentra.tools.others.payload_injection import PayloadInjectorTools
from noxentra.tools.others.socialmedia import SocialMediaBruteforceTools
from noxentra.tools.others.socialmedia_finder import SocialMediaFinderTools
from noxentra.tools.others.web_crawling import WebCrawlingTools
from noxentra.tools.others.wifi_jamming import WifiJammingTools


class HatCloud(Noxentra):
    TITLE = "HatCloud(Bypass CloudFlare for IP)"
    DESCRIPTION = "HatCloud build in Ruby. It makes bypass in CloudFlare for " \
                  "discover real IP."
    INSTALL_COMMANDS: ClassVar = ["git clone https://github.com/HatBashBR/HatCloud.git"]
    PROJECT_URL = "https://github.com/HatBashBR/HatCloud"

    def run(self):
        from noxentra.config import get_tools_dir
        site = Prompt.ask("Enter Site")
        # Bug 3 fix: os.chdir() replaced with cwd= parameter
        subprocess.run(
            ["sudo", "ruby", "hatcloud.rb", "-b", site],
            cwd=str(get_tools_dir() / "HatCloud"),
            check=False,
        )


class OtherTools(NoxentraCollection):
    TITLE = "Other tools"
    TOOLS: ClassVar = [
        SocialMediaBruteforceTools(),
        AndroidAttackTools(),
        HatCloud(),
        IDNHomographAttackTools(),
        EmailVerifyTools(),
        HashCrackingTools(),
        WifiJammingTools(),
        SocialMediaFinderTools(),
        PayloadInjectorTools(),
        WebCrawlingTools(),
        MixTools()
    ]

if __name__ == "__main__":
    tools = OtherTools()
    tools.show_options()
