from PySide6 import QtWidgets

class TextViewerDialog(QtWidgets.QDialog):
    def __init__(self, text, strings, parent=None):
        super().__init__(parent)
        self.strings = strings["text_viewer"]
        self.setWindowTitle(self.strings["title"])
        self.setMinimumSize(400, 300)

        self.text_to_copy = text
        layout = QtWidgets.QVBoxLayout(self)

        self.text_edit = QtWidgets.QTextEdit()
        self.text_edit.setPlainText(text)
        self.text_edit.setReadOnly(True)
        layout.addWidget(self.text_edit)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()

        copy_button = QtWidgets.QPushButton(self.strings["copy_button"])
        copy_button.clicked.connect(self.copy_text)
        button_layout.addWidget(copy_button)

        close_button = QtWidgets.QPushButton(self.strings["close_button"])
        close_button.clicked.connect(self.accept)
        button_layout.addWidget(close_button)

        layout.addLayout(button_layout)

    def copy_text(self):
        clipboard = QtWidgets.QApplication.clipboard()
        clipboard.setText(self.text_to_copy)