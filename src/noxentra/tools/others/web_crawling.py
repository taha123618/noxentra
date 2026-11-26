from typing import ClassVar

from noxentra.core import Noxentra, NoxentraCollection


class GoSpider(Noxentra):
    TITLE = "Gospider"
    DESCRIPTION = "Gospider - Fast web spider written in Go"
    INSTALL_COMMANDS: ClassVar = ["sudo go get -u github.com/jaeles-project/gospider"]
    PROJECT_URL = "https://github.com/jaeles-project/gospider"

    def __init__(self):
        super().__init__(runnable = False)


class WebCrawlingTools(NoxentraCollection):
    TITLE = "Web crawling"
    TOOLS: ClassVar = [GoSpider()]

if __name__ == "__main__":
    tools = WebCrawlingTools()
    tools.show_options()
