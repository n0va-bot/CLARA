from PySide6 import QtCore, QtGui, QtWidgets

from core.app_launcher import list_apps, launch

class AppLauncherDialog(QtWidgets.QDialog):
    def __init__(self, strings, parent=None):
        super().__init__(parent)
        self.strings = strings["app_launcher"]
        self.setWindowTitle(self.strings["title"])
        self.setMinimumSize(600, 400)
        
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        
        # Search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText(self.strings["placeholder"])
        self.search_box.textChanged.connect(self.filter_apps)
        layout.addWidget(self.search_box)
        
        # Apps list widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemClicked.connect(self.launch_app)
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        close_button = QtWidgets.QPushButton(self.strings["close_button"])
        close_button.clicked.connect(self.close)
        
        button_layout.addStretch()
        button_layout.addWidget(close_button)
        layout.addLayout(button_layout)
        
        self.setLayout(layout)
        
        # Load apps
        self.load_apps()
        
        # Focus search box
        self.search_box.setFocus()
    
    def load_apps(self):
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
            self.apps = list_apps()
            self.apps.sort(key=lambda x: x.name.lower())
            self.populate_list(self.apps)
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.strings["load_error_title"], self.strings["load_error_text"].format(e=e))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()
    
    def populate_list(self, apps):
        self.list_widget.clear()
        for app in apps:
            item = QtWidgets.QListWidgetItem(app.name)
            item.setData(QtCore.Qt.UserRole, app) #type: ignore
            
            # Set tooltip with GenericName and Comment
            tooltip_parts = []
            if app.generic_name:
                tooltip_parts.append(app.generic_name)
            if app.comment:
                tooltip_parts.append(app.comment)
            if tooltip_parts:
                item.setToolTip("\n".join(tooltip_parts))

            # Try to load the icon
            if app.icon:
                icon = QtGui.QIcon.fromTheme(app.icon)
                if not icon.isNull():
                    item.setIcon(icon)
            
            self.list_widget.addItem(item)
    
    def filter_apps(self, text):
        if not text:
            self.populate_list(self.apps)
            return
        
        text_lower = text.lower()
        filtered_apps = [
            app for app in self.apps if 
            text_lower in app.name.lower() or
            (app.generic_name and text_lower in app.generic_name.lower()) or
            (app.comment and text_lower in app.comment.lower())
        ]
        self.populate_list(filtered_apps)
    
    def launch_app(self, item: QtWidgets.QListWidgetItem):
        if not item:
            return
        
        app = item.data(QtCore.Qt.UserRole) #type: ignore
        if app:
            try:
                launch(app)
                self.close()
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, self.strings["launch_error_title"], 
                                              self.strings["launch_error_text"].format(app_name=app.name, e=e))