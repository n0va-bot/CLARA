#!/usr/bin/env python3
"""
desktop_pet_x11.py
X11-only: shows a frameless, always-on-top pet using pet.png.
Transparent pixels are click-through via a per-pixel mask (setMask).
"""
import sys
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

ASSET = Path(__file__).with_name("pet.png")


class PetWindow(QtWidgets.QWidget):
    def __init__(self):
        super().__init__()

        # Ensure X11 (xcb) — exit if not
        platform = QtGui.QGuiApplication.platformName().lower()
        if not platform.startswith("xcb"):
            raise SystemExit(
                f"desktop_pet_x11.py requires X11 (platformName={platform}). Exiting."
            )

        # Window flags: frameless, always-on-top, tool window (no taskbar entry)
        flags = (
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setWindowFlags(flags)
        # Let the window be transparent where the PNG is transparent
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Load pixmap
        pix = QtGui.QPixmap(str(ASSET))
        if pix.isNull():
            raise SystemExit(f"Could not load image: {ASSET}")

        # Show pixmap in a label
        self.label = QtWidgets.QLabel(self)
        self.label.setPixmap(pix)
        self.label.resize(pix.size())
        self.resize(pix.size())

        # Apply per-pixel mask from alpha channel so transparent areas are outside the window shape.
        img = pix.toImage()
        if img.hasAlphaChannel():
            # createAlphaMask returns a QImage where alpha pixels are white/black (suitable for QBitmap)
            mask_img = img.createAlphaMask()
            mask = QtGui.QBitmap.fromImage(mask_img)
            self.setMask(mask)
        else:
            # No alpha channel: warn but continue (window will be rectangular and not click-through)
            print("Warning: pet.png has no alpha channel; per-pixel click-through unavailable.")

        # System tray
        self.tray = QtWidgets.QSystemTrayIcon(self)
        # Prefer a small icon; QIcon will scale automatically
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))
        menu = QtWidgets.QMenu()
        menu.addAction("Hide/Show", self.toggle_visible)
        menu.addSeparator()
        menu.addAction("Quit", QtWidgets.QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

        # Dragging support
        self._drag_pos = None

    # Drag only when clicking opaque pixels
    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:
            # global pos - top-left -> offset
            self._drag_pos = event.globalPosition().toPoint() - self.frameGeometry().topLeft()
            event.accept()
        elif event.button() == QtCore.Qt.RightButton:
            # show tray menu at pointer
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
    app.setApplicationName("DesktopPetX11")

    pet = PetWindow()
    pet.move(200, 200)
    pet.show()

    print("Desktop pet started (X11). Transparent pixels are click-through.")
    sys.exit(app.exec())


if __name__ == "__main__":
    main()