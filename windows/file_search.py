from PySide6 import QtCore, QtGui, QtWidgets
import os

class FileSearchResults(QtWidgets.QDialog):
    def __init__(self, results, strings, parent=None):
        super().__init__(parent)
        self.strings = strings["file_search"]
        self.setWindowTitle(self.strings["results_title"])
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
        file_path = item.text()
        if os.path.exists(file_path):
            directory = os.path.dirname(file_path)
            url = QtCore.QUrl.fromLocalFile(directory)
            QtGui.QDesktopServices.openUrl(url)
