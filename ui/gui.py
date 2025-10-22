#!/usr/bin/python3
import sys
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

ASSET = Path(__file__).with_name("2ktan.png")

class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()

        flags = (
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )

        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)
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
        menu = QtWidgets.QMenu()
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
        """Periodically ensure the window stays on top"""
        if self.isVisible():
            self.raise_()
            self.activateWindow()

    def showEvent(self, event):
        """Ensure window is on top when shown"""
        super().showEvent(event)
        self.raise_()
        self.activateWindow()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            self.tray.contextMenu().popup(event.globalPosition().toPoint())

    def mouseMoveEvent(self, event: QtGui.QMouseEvent):
        if self._drag_pos and (event.buttons() & QtCore.Qt.LeftButton):
            self.move(event.globalPosition().toPoint() - self._drag_pos)

    def mouseReleaseEvent(self, event: QtGui.QMouseEvent):
        self._drag_pos = None
        self.raise_()

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    pet = MainWindow()
    
    # bottom right corner
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)

    pet.show()

    sys.exit(app.exec())