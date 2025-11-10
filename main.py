#!/usr/bin/python3
import json
import sys
import threading
from pathlib import Path

from PySide6 import QtWidgets

from core.app_launcher import list_apps
from core.config import config
from core.discord_presence import presence
from core.dukto import DuktoProtocol
from core.updater import is_update_available, update_repository
from windows.main_window import MainWindow

STRINGS_PATH = Path(__file__).parent / "strings" / "personality_en.json"


def preload_apps():
    print("Preloading application list...")
    list_apps()
    print("Application list preloaded.")


def main():
    app = QtWidgets.QApplication(sys.argv)

    try:
        with open(STRINGS_PATH, "r", encoding="utf-8") as f:
            strings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading strings file: {e}")
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical)  # type: ignore
        error_dialog.setText(
            f"Could not load required strings file from:\n{STRINGS_PATH}"
        )
        error_dialog.setWindowTitle("Fatal Error")
        error_dialog.exec()
        sys.exit(1)

    app.setApplicationName("CLARA")

    restart = "--restart" in sys.argv
    no_quit = "--no-quit" in sys.argv
    noupdate = "--no-update" in sys.argv

    if not noupdate and config.get("auto_update", True):
        update_available = is_update_available()
        if update_available:
            update_repository()

    # Start preloading apps in the background
    preload_thread = threading.Thread(target=preload_apps, daemon=True)
    preload_thread.start()

    dukto_handler = DuktoProtocol()
    dukto_handler.set_ports(
        udp_port=config.get("dukto_udp_port", 4644),
        tcp_port=config.get("dukto_tcp_port", 4644),
    )

    pet = MainWindow(
        dukto_handler=dukto_handler,
        strings=strings,
        config=config,
        restart=restart,
        no_quit=no_quit,
    )

    if config.get("discord_presence", True):
        presence.start()

    dukto_handler.initialize()
    dukto_handler.say_hello()

    pet.show()

    app.aboutToQuit.connect(presence.end)
    app.aboutToQuit.connect(dukto_handler.shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
