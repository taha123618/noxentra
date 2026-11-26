import subprocess

from noxentra.core import Noxentra, NoxentraCollection, console, validate_input


class SteganoHide(Noxentra):
    TITLE = "SteganoHide"
    INSTALL_COMMANDS = ["sudo apt-get install steghide -y"]

    def run(self):
        choice_run = input(
            "[1] Hide\n"
            "[2] Extract\n"
            "[99]Cancel\n"
            ">> "
        )
        choice_run = validate_input(choice_run, [1, 2, 99])
        if choice_run is None:
            console.print("[bold red]Please choose a valid input[/bold red]")
            return self.run()

        if choice_run == 99:
            return

        if choice_run == 1:
            file_hide = input("Enter Filename to Embed (1.txt) >> ")
            file_to_be_hide = input("Enter Cover Filename (test.jpeg) >> ")
            if not file_hide.strip() or not file_to_be_hide.strip():
                console.print("[bold red]Both filenames are required[/bold red]")
                return
            subprocess.run(["steghide", "embed", "-cf", file_to_be_hide, "-ef", file_hide])

        elif choice_run == 2:
            from_file = input("Enter Filename to Extract Data From >> ")
            if not from_file.strip():
                console.print("[bold red]A filename is required[/bold red]")
                return
            subprocess.run(["steghide", "extract", "-sf", from_file])


class SteganographyTools(NoxentraCollection):
    TITLE = "Steganography Tools"
    TOOLS = [SteganoHide()]

if __name__ == "__main__":
    tools = SteganographyTools()
    tools.show_options()
