from PySide6 import QtWidgets, QtCore

class CalculatorDialog(QtWidgets.QDialog):
    def __init__(self, strings, parent=None):
        super().__init__(parent)
        self.strings = strings["calculator"]
        self.setWindowTitle(self.strings["title"])
        self.setMinimumWidth(350)

        # Main layout
        layout = QtWidgets.QVBoxLayout(self)
        
        # text box
        self.equation_box = QtWidgets.QLineEdit()
        self.equation_box.setPlaceholderText("Type a mathematical equation...")
        self.equation_box.textChanged.connect(self.update_result)
        layout.addWidget(self.equation_box)

        # label
        self.result_label = QtWidgets.QLabel()
        self.result_label.setTextInteractionFlags(QtCore.Qt.TextSelectableByMouse) # type: ignore
        self.result_label.setStyleSheet("padding: 5px; border: 1px solid #ccc; border-radius: 4px;")
        layout.addWidget(self.result_label)

        # copy button
        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addStretch()
        copy_button = QtWidgets.QPushButton(self.strings.get("copy_button", "Copy"))
        copy_button.clicked.connect(self.copy_to_clipboard)
        button_layout.addWidget(copy_button)
        layout.addLayout(button_layout)

        self.setLayout(layout)
        self.equation_box.setFocus()
    
    def update_result(self, text: str):
        if not text.strip():
            self.result_label.setText("")
            return
        
        try:
            result = eval(text)
            
            self.result_label.setText(str(result))
        except Exception:
            self.result_label.setText("")

    def copy_to_clipboard(self):
        text = self.result_label.text()
        if text:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(text)