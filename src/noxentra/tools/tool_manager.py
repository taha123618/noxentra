import os
import subprocess

from rich.prompt import Confirm

from noxentra.core import Noxentra, NoxentraCollection, console
from noxentra.constants import USER_CONFIG_DIR, REPO_WEB_URL


class UpdateTool(Noxentra):
    TITLE = "Update Tool or System"
    DESCRIPTION = "Update system packages or pull the latest noxentra code"

    def __init__(self):
        super().__init__([
            ("Update System", self.update_sys),
            ("Update Noxentra", self.update_ht),
        ], installable=False, runnable=False)

    def update_sys(self):
        from noxentra.os_detect import CURRENT_OS, PACKAGE_UPDATE_CMDS
        mgr = CURRENT_OS.pkg_manager
        cmd = PACKAGE_UPDATE_CMDS.get(mgr)
        if cmd:
            priv = "" if (CURRENT_OS.system == "macos" or os.geteuid() == 0) else "sudo "
            # shell=True needed — cmd contains && chains; strings are hardcoded, not user input
            subprocess.run(f"{priv}{cmd}", shell=True, check=False)
        else:
            console.print("[warning]Unknown package manager — update manually.[/warning]")

    def update_ht(self):
        # noxentra ships as a standard package (pipx/pip/.deb/docker). It can't
        # reliably self-update its own installed package from inside, so show the
        # right command for each channel instead of a broken git-pull.
        console.print("[bold cyan]Update noxentra with the command for how you installed it:[/bold cyan]")
        console.print("  pipx     [success]pipx upgrade noxentra[/success]")
        console.print("  pip      [success]pip install --upgrade noxentra[/success]")
        console.print("  .deb     download the latest .deb, then [success]sudo apt install ./<file>.deb[/success]")
        console.print("  docker   [success]docker pull taha123618/noxentra:latest[/success]")
        console.print(f"[dim]Latest release: {REPO_WEB_URL}/releases/latest[/dim]")


class UninstallTool(Noxentra):
    TITLE = "Uninstall Noxentra"
    DESCRIPTION = "Remove noxentra from system"

    def __init__(self):
        super().__init__([
            ("Uninstall", self.uninstall),
        ], installable=False, runnable=False)

    def uninstall(self):
        import shutil
        # Remove the package itself with the channel's own command (we can't
        # uninstall our own pipx/pip/apt package from inside it). We can clean up
        # the one thing we own regardless of install method: the ~/.noxentra data.
        console.print("[warning]Remove the noxentra package with the command for how you installed it:[/warning]")
        console.print("  pipx     [success]pipx uninstall noxentra[/success]")
        console.print("  pip      [success]pip uninstall noxentra[/success]")
        console.print("  .deb     [success]sudo apt remove python3-noxentra[/success]")
        console.print("  docker   [success]docker rmi taha123618/noxentra:latest[/success]")

        if USER_CONFIG_DIR.exists() and Confirm.ask(
                f"Remove your data + installed tools at {USER_CONFIG_DIR} now?", default=False):
            shutil.rmtree(str(USER_CONFIG_DIR), ignore_errors=True)
            console.print(f"[success]✔ Removed {USER_CONFIG_DIR}[/success]")


class ToolManager(NoxentraCollection):
    TITLE = "Update or Uninstall | Noxentra"
    TOOLS = [
        UpdateTool(),
        UninstallTool(),
    ]


if __name__ == "__main__":
    manager = ToolManager()
    manager.show_options()
