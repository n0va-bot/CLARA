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

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    pet = MainWindow()
    pet.move(200, 200)
    pet.show()

    sys.exit(app.exec())