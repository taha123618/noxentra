from typing import ClassVar

from noxentra.core import NoxentraCollection


class ActiveDirectoryTools(NoxentraCollection):
    TITLE = "Active Directory Tools"
    DESCRIPTION = "Tools for AD enumeration, attack path discovery, and credential attacks."
    TOOLS: ClassVar = []
