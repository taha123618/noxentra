
from noxentra.core import Noxentra, NoxentraCollection


class GoSpider(Noxentra):
    TITLE = "Gospider"
    DESCRIPTION = "Gospider - Fast web spider written in Go"
    INSTALL_COMMANDS = ["sudo go get -u github.com/jaeles-project/gospider"]
    PROJECT_URL = "https://github.com/jaeles-project/gospider"

    def __init__(self):
        super().__init__(runnable = False)


class WebCrawlingTools(NoxentraCollection):
    TITLE = "Web crawling"
    TOOLS = [GoSpider()]

if __name__ == "__main__":
    tools = WebCrawlingTools()
    tools.show_options()
