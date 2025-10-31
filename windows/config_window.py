from PySide6 import QtWidgets
from core.config import Config

class ConfigWindow(QtWidgets.QDialog):
    def __init__(self, strings, config: Config, parent=None):
        super().__init__(parent)
        self.strings = strings.get("config_window", {})
        self.config = config
        self.setWindowTitle(self.strings.get("title", "Settings"))
        self.setMinimumWidth(400)

        self.layout = QtWidgets.QVBoxLayout(self)  # type: ignore
        self.form_layout = QtWidgets.QFormLayout()

        # Create widgets for each setting
        self.hotkey_input = QtWidgets.QLineEdit()
        self.discord_presence_check = QtWidgets.QCheckBox()
        self.auto_update_check = QtWidgets.QCheckBox()
        self.http_port_spin = QtWidgets.QSpinBox()
        self.http_port_spin.setRange(1024, 65535)
        self.dukto_udp_port_spin = QtWidgets.QSpinBox()
        self.dukto_udp_port_spin.setRange(1024, 65535)
        self.dukto_tcp_port_spin = QtWidgets.QSpinBox()
        self.dukto_tcp_port_spin.setRange(1024, 65535)
        self.search_engine_combo = QtWidgets.QComboBox()
        self.search_engine_combo.addItems(["brave", "google"])

        # Add widgets to layout
        self.form_layout.addRow(self.strings.get("hotkey_label", "Global Hotkey:"), self.hotkey_input)
        self.form_layout.addRow(self.strings.get("discord_presence_label", "Enable Discord Presence:"), self.discord_presence_check)
        self.form_layout.addRow(self.strings.get("auto_update_label", "Enable Auto-Update:"), self.auto_update_check)
        self.form_layout.addRow(self.strings.get("http_share_port_label", "HTTP Share Port:"), self.http_port_spin)
        self.form_layout.addRow(self.strings.get("dukto_udp_port_label", "Dukto UDP Port:"), self.dukto_udp_port_spin)
        self.form_layout.addRow(self.strings.get("dukto_tcp_port_label", "Dukto TCP Port:"), self.dukto_tcp_port_spin)
        self.form_layout.addRow(self.strings.get("search_engine_label", "Web Search Engine:"), self.search_engine_combo)

        self.layout.addLayout(self.form_layout) #type: ignore

        # Info label
        self.info_label = QtWidgets.QLabel(self.strings.get("restart_note", "Note: Some changes may require a restart."))
        self.info_label.setStyleSheet("font-style: italic; color: grey;")
        self.info_label.setWordWrap(True)
        self.layout.addWidget(self.info_label) #type: ignore

        # Buttons
        self.button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.Save | QtWidgets.QDialogButtonBox.Cancel | QtWidgets.QDialogButtonBox.Reset # type: ignore
        )
        self.button_box.accepted.connect(self.save_config)
        self.button_box.rejected.connect(self.reject)
        reset_button = self.button_box.button(QtWidgets.QDialogButtonBox.Reset) # type: ignore
        if reset_button:
            reset_button.clicked.connect(self.reset_to_defaults)

        self.layout.addWidget(self.button_box) #type: ignore

        self.load_config()

    def load_config(self):
        self.hotkey_input.setText(self.config.get("hotkey", ""))
        self.discord_presence_check.setChecked(self.config.get("discord_presence", True))
        self.auto_update_check.setChecked(self.config.get("auto_update", True))
        self.http_port_spin.setValue(self.config.get("http_share_port", 8080))
        self.dukto_udp_port_spin.setValue(self.config.get("dukto_udp_port", 4644))
        self.dukto_tcp_port_spin.setValue(self.config.get("dukto_tcp_port", 4644))
        self.search_engine_combo.setCurrentText(self.config.get("search_engine", "brave"))

    def save_config(self):
        self.config.set("hotkey", self.hotkey_input.text())
        self.config.set("discord_presence", self.discord_presence_check.isChecked())
        self.config.set("auto_update", self.auto_update_check.isChecked())
        self.config.set("http_share_port", self.http_port_spin.value())
        self.config.set("dukto_udp_port", self.dukto_udp_port_spin.value())
        self.config.set("dukto_tcp_port", self.dukto_tcp_port_spin.value())
        self.config.set("search_engine", self.search_engine_combo.currentText())
        self.accept()
    
    def reset_to_defaults(self):
        reply = QtWidgets.QMessageBox.question(
            self,
            self.strings.get("reset_title", "Confirm Reset"),
            self.strings.get("reset_text", "Are you sure?"),
            QtWidgets.QMessageBox.Yes | QtWidgets.QMessageBox.No, # type: ignore
            QtWidgets.QMessageBox.No # type: ignore
        )
        if reply == QtWidgets.QMessageBox.Yes: # type: ignore
            self.config.reset()
            self.load_config()