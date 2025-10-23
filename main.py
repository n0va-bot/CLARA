#!/usr/bin/python3
import sys, os, subprocess
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

from core.file_search import find
from core.web_search import MullvadLetaWrapper

ASSET = Path(__file__).parent / "assets" / "2ktan.png"

class FileSearchResults(QtWidgets.QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Results")
        self.setMinimumSize(600, 400)

        # results list widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(results)
        self.list_widget.itemDoubleClicked.connect(self.open_file_location)

        # layout
        layout = QtWidgets.QVBoxLayout()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def open_file_location(self, item: QtWidgets.QListWidgetItem):
        """Opens the directory containing the selected file."""
        file_path = item.text()
        if os.path.exists(file_path):
            directory = os.path.dirname(file_path)
            url = QtCore.QUrl.fromLocalFile(directory)
            QtGui.QDesktopServices.openUrl(url)

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self, restart=False):
        super().__init__()

        flags = (
            QtCore.Qt.FramelessWindowHint                              #type: ignore
            | QtCore.Qt.WindowStaysOnTopHint                           #type: ignore
            | QtCore.Qt.Tool                                           #type: ignore
            | QtCore.Qt.WindowDoesNotAcceptFocus                       #type: ignore
        )

        self.setWindowFlags(flags)         
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)          #type: ignore
        pix = QtGui.QPixmap(str(ASSET))

        self.label = QtWidgets.QLabel(self)
        self.label.setPixmap(pix)
        self.label.resize(pix.size())
        self.resize(pix.size())

        img = pix.toImage()
        mask_img = img.createAlphaMask()
        mask = QtGui.QBitmap.fromImage(mask_img)
        self.setMask(mask)

        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))

        # RIGHT MENU
        right_menu = QtWidgets.QMenu()
        right_menu.addAction("Search Files", self.start_file_search)
        right_menu.addAction("Search Web", self.start_web_search)
        right_menu.addSeparator()
        if restart:
            right_menu.addAction("Restart", self.restart_application)
        right_menu.addAction("Hide/Show", self.toggle_visible)
        right_menu.addSeparator()
        right_menu.addAction("Quit", QtWidgets.QApplication.quit)
        self.tray.setContextMenu(right_menu)
        self.tray.show()

        # LEFT MENU
        self.left_menu = QtWidgets.QMenu()
        self.left_menu.addAction("Search Files", self.start_file_search)
        self.left_menu.addAction("Search Web", self.start_web_search)

        # always on top timer
        self.stay_on_top_timer = QtCore.QTimer(self)
        self.stay_on_top_timer.timeout.connect(self.ensure_on_top)
        self.stay_on_top_timer.start(1000)

    def ensure_on_top(self):
        if self.isVisible():
            self.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:                      #type: ignore
            self.left_menu.popup(event.globalPosition().toPoint())

        elif event.button() == QtCore.Qt.RightButton:                   #type: ignore
            self.tray.contextMenu().popup(event.globalPosition().toPoint())

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def start_file_search(self):
        pattern, ok = QtWidgets.QInputDialog.getText(self, "File Search", "Enter search pattern:")
        
        if ok and pattern:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
                results = find(pattern, root='~')
            except RuntimeError as e:
                QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
                return
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

            if results:
                self.results_dialog = FileSearchResults(results, self)
                self.results_dialog.show()
            else:
                reply = QtWidgets.QMessageBox.question(self, "No Results", "Sorry, I couldn't find anything in your home folder. Would you like me to search the root folder?",
                                                       QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # type: ignore
                        results = find(pattern, root='/')
                    except RuntimeError as e:
                        QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
                        return
                    finally:
                        QtWidgets.QApplication.restoreOverrideCursor()

                    if results:
                        self.results_dialog = FileSearchResults(results, self)
                        self.results_dialog.show()
                    else:
                        QtWidgets.QMessageBox.information(self, "No Results", "Sorry, I couldn't find anything in the root folder either.")

    def start_web_search(self):
        query, ok = QtWidgets.QInputDialog.getText(self, "Web Search", "Enter search query:")        
        if ok and query:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
                leta = MullvadLetaWrapper(engine="brave")
                results = leta.search(query)
            except RuntimeError as e:
                QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
                return
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

    def restart_application(self):
        """Restarts the application."""
        subprocess.Popen([sys.executable] + sys.argv)
        QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    restart_enabled = "--restart" in sys.argv
    pet = MainWindow(restart=restart_enabled)
    
    # bottom right corner
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)

    pet.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()