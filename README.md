# CLARA
### Computer Linguistically Advanced Reactive Assistant

A WIP desktop assistant for Linux and Windows.

![CLARA](/assets/2ktan.png)

(Don't worry, 2k-tan is just a placeholder)

## Features
- App launcher
- File search
- Web search
- Updater
- Super key menu (Doesn't work properly on Windows)
- Local network file and text transfer (Dukto protocol)
- Browser based file and text transfer (HTTP)
- Discord Rich Presence integration
- Calculator

## Requirements
- Python 3
- X11 Desktop
- [`fd`](https://github.com/sharkdp/fd)
- `git`

## Instructions
1. Clone this repository
2. Install all of the modules from `requirements.txt`, either with `pip install -r requirements.txt` or via your distribution's package manager.
3. You will also need to install the `fd` command-line tool for the file search feature to work. (e.g., `sudo apt install fd-find` on Debian/Ubuntu, `sudo pacman -S fd` on Arch Linux).
> For other Linux distros and Windows go [here](https://github.com/sharkdp/fd)
4. Launch `main.py`. Available options:
     - `--restart` Add a restart option to the right click menu
     - `--no-quit` Hide the quit option
     - `--no-super`/`--no-start` Disable the super key menu (recommended on Windows)
     - `--no-update` Don't update automatically on startup

If you want to contribute in any way, PRs (and issues) welcome