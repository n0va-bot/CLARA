#!/usr/bin/python3
import sys, os, subprocess
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

from core.file_search import find

ASSET = Path(__file__).parent / "assets" / "2ktan.png"

class SearchResultsDialog(QtWidgets.QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Results")
        self.setMinimumSize(600, 400)

        # Create a list widget to display the results
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.addItems(results)
        self.list_widget.itemDoubleClicked.connect(self.open_file_location)

        # Set up the layout
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

        # MENU
        menu = QtWidgets.QMenu()
        menu.addAction("Search Files", self.start_file_search)
        if restart:
            menu.addAction("Restart", self.restart_application)
        menu.addAction("Hide/Show", self.toggle_visible)
        menu.addSeparator()
        menu.addAction("Quit", QtWidgets.QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

        self._drag_pos = None

        # Timer to ensure window stays on top
        self.stay_on_top_timer = QtCore.QTimer(self)
        self.stay_on_top_timer.timeout.connect(self.ensure_on_top)
        self.stay_on_top_timer.start(1000)

    def ensure_on_top(self):
        if self.isVisible():
            self.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()

    def mouseDoubleClickEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:                      #type: ignore
            self.start_file_search()
            event.accept()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:                      #type: ignore
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:                   #type: ignore
            self.tray.contextMenu().popup(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_pos and (event.buttons() & QtCore.Qt.LeftButton): #type: ignore
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_pos = None
        self.raise_()

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
                self.results_dialog = SearchResultsDialog(results, self)
                self.results_dialog.show()
            else:
                QtWidgets.QMessageBox.information(self, "No Results", f"No files found matching '{pattern}'.")

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