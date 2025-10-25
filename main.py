#!/usr/bin/python3
import sys, json
from pathlib import Path
from PySide6 import QtWidgets

from core.discord_presence import presence
from core.dukto import DuktoProtocol

from windows.main_window import MainWindow

STRINGS_PATH = Path(__file__).parent / "strings" / "personality_en.json"

def main():
    app = QtWidgets.QApplication(sys.argv)
    
    try:
        with open(STRINGS_PATH, 'r', encoding='utf-8') as f:
            strings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading strings file: {e}")
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical) #type: ignore
        error_dialog.setText(f"Could not load required strings file from:\n{STRINGS_PATH}")
        error_dialog.setWindowTitle("Fatal Error")
        error_dialog.exec()
        sys.exit(1)
        
    app.setApplicationName("CLARA")

    restart = "--restart" in sys.argv
    no_quit = "--no-quit" in sys.argv
    super_menu = not "--no-super" in sys.argv
    
    dukto_handler = DuktoProtocol()
    
    pet = MainWindow(dukto_handler=dukto_handler, strings=strings, restart=restart, no_quit=no_quit, super_menu=super_menu)
    
    presence.start()
    
    dukto_handler.initialize()
    dukto_handler.say_hello()
    
    # bottom right corner
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)

    pet.show()

    app.aboutToQuit.connect(presence.end)
    app.aboutToQuit.connect(dukto_handler.shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()