
from noxentra.core import Noxentra, NoxentraCollection


class EvilURL(Noxentra):
    ARCHIVED = True
    ARCHIVED_REASON = "Upstream repo archived by author (last commit 2026-05)"
    TITLE = "EvilURL"
    DESCRIPTION = "Generate unicode evil domains for IDN Homograph Attack " \
                  "and detect them."
    INSTALL_COMMANDS = ["git clone https://github.com/UndeadSec/EvilURL.git"]
    RUN_COMMANDS = ["cd EvilURL;python3 evilurl.py"]
    PROJECT_URL = "https://github.com/UndeadSec/EvilURL"


class IDNHomographAttackTools(NoxentraCollection):
    TITLE = "IDN Homograph Attack"
    TOOLS = [EvilURL()]

if __name__ == "__main__":
    tools = IDNHomographAttackTools()
    tools.show_options()
