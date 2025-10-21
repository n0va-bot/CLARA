import sys
import os
import io
import base64
from pathlib import Path

try:
    from openai import OpenAI
except ImportError:
    print("OpenAI SDK not found.")
    print("Please install it using: pip install openai")
    sys.exit(1)

from PySide6 import QtCore, QtGui, QtWidgets

# --- CONFIGURATION ---
MODEL_NAME = "mistralai/mistral-small-3.2-24b-instruct:free"

# --- ASSET PATH ---
ASSET = Path(__file__).with_name("2ktan.png")
if not ASSET.exists():
    print(f"Asset file not found at: {ASSET}")
    sys.exit(1)


# --- Worker Thread for AI---
class Worker(QtCore.QObject):
    finished = QtCore.Signal(str)

    def __init__(self, question, img_base64):
        super().__init__()
        self.question = question
        self.img_base64 = img_base64

    @QtCore.Slot()
    def run(self):
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=os.environ.get("OPENROUTER_API_KEY"),
            )
            messages = [
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": f"Analyze the screenshot and answer this question: {self.question}"},
                        {"type": "image_url", "image_url": {"url": f"data:image/png;base64,{self.img_base64}"}}
                    ]
                }
            ]
            completion = client.chat.completions.create(
                model=MODEL_NAME,
                messages=messages,
                max_tokens=4096,
            )
            answer = completion.choices[0].message.content
        except Exception as e:
            answer = (f"Could not get an answer from the AI.\n\nError: {e}")
        self.finished.emit(answer)


class MainWindow(QtWidgets.QMainWindow):
    def __init__(self):
        super().__init__()
        self.thread = None
        self.worker = None
        self.answer_dialog = None

        flags = (
            QtCore.Qt.FramelessWindowHint
            | QtCore.Qt.WindowStaysOnTopHint
            | QtCore.Qt.Tool
        )
        self.setWindowFlags(flags)
        self.setAttribute(QtCore.Qt.WA_TranslucentBackground)

        # Main pet image label
        pix = QtGui.QPixmap(str(ASSET))
        self.label = QtWidgets.QLabel(self)
        self.label.setPixmap(pix)
        self.label.resize(pix.size())
        self.resize(pix.size())

        # Thinking label
        self.thinking_label = QtWidgets.QLabel("Thinking...", self)
        self.thinking_label.setAlignment(QtCore.Qt.AlignmentFlag.AlignCenter)
        self.thinking_label.setStyleSheet("""
            background-color: rgba(0, 0, 0, 180);
            color: white;
            font-size: 14px;
            border-radius: 10px;
            padding: 10px;
        """)
        self.thinking_label.setFixedSize(120, 50)
        self.thinking_label.move(
            (self.width() - self.thinking_label.width()) // 2,
            (self.height() - self.thinking_label.height()) // 2
        )
        self.thinking_label.hide()

        # Masking for transparency
        img = pix.toImage()
        mask = QtGui.QBitmap.fromImage(img.createAlphaMask())
        self.setMask(mask)

        # System Tray Icon setup
        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))
        menu = QtWidgets.QMenu()
        menu.addAction("Hide/Show", self.toggle_visible)
        menu.addAction("Ask about screen", self.ask_about_screen)
        menu.addSeparator()
        menu.addAction("Quit", QtWidgets.QApplication.quit)
        self.tray.setContextMenu(menu)
        self.tray.show()

        self._drag_pos = None

    def ask_about_screen(self):
        if self.thread and self.thread.isRunning():
            return

        self.hide()
        QtCore.QCoreApplication.processEvents()
        screen = QtWidgets.QApplication.primaryScreen()
        screenshot = screen.grabWindow(0)
        self.show()

        question, ok = QtWidgets.QInputDialog.getText(self, "Ask About The Screen", "What is your question?")

        if ok and question:
            buffer = QtCore.QBuffer()
            buffer.open(QtCore.QIODevice.WriteOnly)
            screenshot.save(buffer, "PNG")
            img_base64 = base64.b64encode(buffer.data()).decode("utf-8")

            self.thread = QtCore.QThread()
            self.worker = Worker(question, img_base64)
            self.worker.moveToThread(self.thread)

            self.thread.started.connect(self.worker.run)
            self.worker.finished.connect(self.on_ai_request_finished)
            self.worker.finished.connect(self.thread.quit)
            self.worker.finished.connect(self.worker.deleteLater)
            self.thread.finished.connect(self.thread.deleteLater)
            
            self.thread.start()

            self.thinking_label.show()
            self.thinking_label.raise_()

    def on_ai_request_finished(self, answer):
        self.thinking_label.hide()
        self.show_answer_dialog(answer)

    def show_answer_dialog(self, answer_text):
        self.answer_dialog = QtWidgets.QDialog(self)
        self.answer_dialog.setWindowTitle("AI's Answer")
        self.answer_dialog.setMinimumSize(600, 400)
        self.answer_dialog.setModal(True)

        layout = QtWidgets.QVBoxLayout(self.answer_dialog)
        text_area = QtWidgets.QTextEdit()
        text_area.setReadOnly(True)
        text_area.setText(answer_text)
        layout.addWidget(text_area)
        close_button = QtWidgets.QPushButton("Close")
        close_button.clicked.connect(self.answer_dialog.accept)
        layout.addWidget(close_button)

        self.answer_dialog.show()

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
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)
    pet.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()