# CLARA
### Computer Linguistically Advanced Reactive Assistant

A ***very*** WIP desktop assistant for X11-based desktops.

(Don't worry, 2k-tan is just a placeholder)

## Features
- App launcher
- File search
- Web search
- Updater (git)
- Super key menu
- Local network file and text transfer (Dukto protocol)
- Discord Rich Presence integration

## Instructions
1. Clone this repository
2. Install all of the modules from `requirements.txt`, either with `pip install -r requirements.txt` or via your distribution's package manager.
3. You will also need to install the `fd` command-line tool for the file search feature to work. (e.g., `sudo apt install fd-find` on Debian/Ubuntu, `sudo pacman -S fd` on Arch Linux).
4. Launch `main.py`. Available options:
     - `--restart` Add a restart option to the right click menu
     - `--no-quit` Hide the quit option
     - `--no-super` Disable the super key menu

If you want to contribute in any way, PRs (and issues) welcome