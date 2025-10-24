#!/usr/bin/python3
import sys, os, subprocess, json
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from pynput import keyboard

from core.file_search import find
from core.web_search import MullvadLetaWrapper
from core.discord_presence import presence
from core.app_launcher import list_apps, launch
from core.updater import update_repository, is_update_available
from core.dukto import DuktoProtocol, Peer

ASSET = Path(__file__).parent / "assets" / "2ktan.png"
STRINGS_PATH = Path(__file__).parent / "strings" / "personality_en.json"

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
        filtered_apps = [app for app in self.apps if text_lower in app.name.lower()]
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


class WebSearchResults(QtWidgets.QDialog):
    def __init__(self, results, strings, parent=None):
        super().__init__(parent)
        self.strings = strings["web_search"]
        self.setWindowTitle(self.strings["results_title"].format(query=results['query']))
        self.setMinimumSize(800, 600)
        
        self.results = results
        self.strings_full = strings
        
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        
        # Info label
        info_text = self.strings["info_base"].format(engine=results['engine'], page=results['page'])
        if results.get('cached'):
            info_text += self.strings["info_cached"]
        info_label = QtWidgets.QLabel(info_text)
        info_label.setStyleSheet("color: gray; font-size: 10px; padding: 5px;")
        layout.addWidget(info_label)
        
        # Scroll area
        scroll = QtWidgets.QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(QtCore.Qt.ScrollBarAlwaysOff)  # type: ignore
        
        # Container
        container = QtWidgets.QWidget()
        container_layout = QtWidgets.QVBoxLayout(container)
        container_layout.setSpacing(15)
        
        # Add infobox
        if results.get('infobox'):
            infobox_widget = self._create_infobox_widget(results['infobox'])
            container_layout.addWidget(infobox_widget)
            
            # Separator
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)   #type: ignore
            line.setFrameShadow(QtWidgets.QFrame.Sunken) #type: ignore
            container_layout.addWidget(line)
        
        # Add news
        if results.get('news'):
            news_label = QtWidgets.QLabel(self.strings["news_header"])
            news_label.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 3px; padding: 8px;")
            container_layout.addWidget(news_label)
            
            for news_item in results['news'][:5]:  # Show first 5 news items
                news_widget = self._create_news_widget(news_item)
                container_layout.addWidget(news_widget)
            
            # Separator
            line = QtWidgets.QFrame()
            line.setFrameShape(QtWidgets.QFrame.HLine)   #type: ignore
            line.setFrameShadow(QtWidgets.QFrame.Sunken) #type: ignore
            container_layout.addWidget(line)
        
        # Add results
        for result in results.get('results', []):
            result_widget = self._create_result_widget(result)
            container_layout.addWidget(result_widget)
        
        container_layout.addStretch()
        scroll.setWidget(container)
        layout.addWidget(scroll)
        
        # Navigation buttons
        nav_layout = QtWidgets.QHBoxLayout()
        
        if results['page'] > 1:
            prev_button = QtWidgets.QPushButton(self.strings["prev_button"])
            prev_button.clicked.connect(lambda: self.load_page(results['page'] - 1))
            nav_layout.addWidget(prev_button)
        
        nav_layout.addStretch()
        
        if results.get('has_next_page'):
            next_button = QtWidgets.QPushButton(self.strings["next_button"])
            next_button.clicked.connect(lambda: self.load_page(results['page'] + 1))
            nav_layout.addWidget(next_button)
        
        layout.addLayout(nav_layout)
        
        self.setLayout(layout)
    
    def _create_infobox_widget(self, infobox):
        widget = QtWidgets.QFrame()
        widget.setFrameShape(QtWidgets.QFrame.StyledPanel) #type: ignore
        widget.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 3px; padding: 8px;")
        
        layout = QtWidgets.QVBoxLayout(widget)
        
        # Title
        title = QtWidgets.QLabel(infobox.get('title', ''))
        title.setStyleSheet("font-weight: bold; font-size: 16px;")
        title.setWordWrap(True)
        layout.addWidget(title)
        
        # Subtitle
        if infobox.get('subtitle'):
            subtitle = QtWidgets.QLabel(infobox['subtitle'])
            subtitle.setStyleSheet("color: gray; font-size: 12px;")
            subtitle.setWordWrap(True)
            layout.addWidget(subtitle)
        
        # URL
        if infobox.get('url'):
            url_label = QtWidgets.QLabel(f'<a href="{infobox["url"]}">{infobox["url"]}</a>')
            url_label.setOpenExternalLinks(True)
            url_label.setStyleSheet("color: blue; font-size: 11px;")
            layout.addWidget(url_label)
        
        # Description
        if infobox.get('description'):
            desc = QtWidgets.QLabel(infobox['description'])
            desc.setWordWrap(True)
            desc.setStyleSheet("margin-top: 5px;")
            layout.addWidget(desc)
        
        return widget
    
    def _create_news_widget(self, news_item):
        widget = QtWidgets.QFrame()
        widget.setFrameShape(QtWidgets.QFrame.Box) #type: ignore
        widget.setStyleSheet("border: 1px solid #e0e0e0; border-radius: 3px; padding: 8px;")
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(3)
        
        # Source
        source_label = QtWidgets.QLabel(news_item.get('source', ''))
        source_label.setStyleSheet("color: green; font-size: 10px;")
        layout.addWidget(source_label)
        
        # Title (clickable)
        title = QtWidgets.QLabel(f'<a href="{news_item["url"]}">{news_item.get("title", "")}</a>')
        title.setOpenExternalLinks(True)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 12px;")
        layout.addWidget(title)
        
        # Timestamp
        if news_item.get('timestamp'):
            time_label = QtWidgets.QLabel(news_item['timestamp'])
            time_label.setStyleSheet("color: gray; font-size: 9px;")
            layout.addWidget(time_label)
        
        return widget
    
    def _create_result_widget(self, result):
        widget = QtWidgets.QFrame()
        widget.setFrameShape(QtWidgets.QFrame.NoFrame) #type: ignore
        widget.setStyleSheet("padding: 5px;")
        
        layout = QtWidgets.QVBoxLayout(widget)
        layout.setSpacing(5)
        
        # Display URL
        if result.get('display_url'):
            url_label = QtWidgets.QLabel(result['display_url'])
            url_label.setStyleSheet("color: green; font-size: 11px;")
            layout.addWidget(url_label)
        
        # Title
        title = QtWidgets.QLabel(f'<a href="{result["url"]}">{result.get("title", "")}</a>')
        title.setOpenExternalLinks(True)
        title.setWordWrap(True)
        title.setStyleSheet("font-size: 14px; color: #1a0dab;")
        layout.addWidget(title)
        
        # Snippet
        if result.get('snippet'):
            snippet = QtWidgets.QLabel(result['snippet'])
            snippet.setWordWrap(True)
            snippet.setStyleSheet("color: #545454; font-size: 12px;")
            layout.addWidget(snippet)
        
        return widget
    
    def load_page(self, page_num):
        try:
            QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # type: ignore
            leta = MullvadLetaWrapper(engine=self.results['engine'])
            new_results = leta.search(self.results['query'], page=page_num)
            
            # Close current dialog and open new one
            new_dialog = WebSearchResults(new_results, self.strings_full, self.parent())
            new_dialog.show()
            self.close()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, self.strings["search_error_title"], self.strings["search_error_text"].format(e=e))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()


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


class MainWindow(QtWidgets.QMainWindow):
    show_menu_signal = QtCore.Signal()
    
    # Dukto signals
    peer_added_signal = QtCore.Signal(Peer)
    peer_removed_signal = QtCore.Signal(Peer)
    receive_request_signal = QtCore.Signal(str)
    progress_update_signal = QtCore.Signal(int, int)
    receive_start_signal = QtCore.Signal(str)
    receive_complete_signal = QtCore.Signal(list, int)
    receive_text_signal = QtCore.Signal(str, int)
    send_start_signal = QtCore.Signal(str)
    send_complete_signal = QtCore.Signal(list)
    dukto_error_signal = QtCore.Signal(str)


    def __init__(self, dukto_handler, strings, restart=False, no_quit=False, super_menu=True):
        super().__init__()
        
        self.strings = strings

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

        self.super_menu = super_menu
        self.dukto_handler = dukto_handler
        self.progress_dialog = None

        # Connect Dukto callbacks to emit signals
        self.dukto_handler.on_peer_added = lambda peer: self.peer_added_signal.emit(peer)
        self.dukto_handler.on_peer_removed = lambda peer: self.peer_removed_signal.emit(peer)
        self.dukto_handler.on_receive_request = lambda ip: self.receive_request_signal.emit(ip)
        self.dukto_handler.on_transfer_progress = lambda total, rec: self.progress_update_signal.emit(total, rec)
        self.dukto_handler.on_receive_start = lambda ip: self.receive_start_signal.emit(ip)
        self.dukto_handler.on_receive_complete = lambda files, size: self.receive_complete_signal.emit(files, size)
        self.dukto_handler.on_receive_text = lambda text, size: self.receive_text_signal.emit(text, size)
        self.dukto_handler.on_send_start = lambda ip: self.send_start_signal.emit(ip)
        self.dukto_handler.on_send_complete = lambda files: self.send_complete_signal.emit(files)
        self.dukto_handler.on_error = lambda msg: self.dukto_error_signal.emit(msg)
        
        # Connect signals to GUI slots
        self.peer_added_signal.connect(self.update_peer_menus)
        self.peer_removed_signal.connect(self.update_peer_menus)
        self.receive_request_signal.connect(self.show_receive_confirmation)
        self.progress_update_signal.connect(self.update_progress_dialog)
        self.receive_start_signal.connect(self.handle_receive_start)
        self.receive_complete_signal.connect(self.handle_receive_complete)
        self.receive_text_signal.connect(self.handle_receive_text)
        self.send_start_signal.connect(self.handle_send_start)
        self.send_complete_signal.connect(self.handle_send_complete)
        self.dukto_error_signal.connect(self.handle_dukto_error)

        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))
        
        s = self.strings["main_window"]["right_menu"]

        # RIGHT MENU
        right_menu = QtWidgets.QMenu()
        right_menu.addAction(s["launch_app"], self.start_app_launcher)
        right_menu.addAction(s["search_files"], self.start_file_search)
        right_menu.addAction(s["search_web"], self.start_web_search)
        right_menu.addSeparator()
        send_menu_right = right_menu.addMenu(s["send_menu"])
        self.send_files_submenu_right = send_menu_right.addMenu(s["send_files_submenu"])
        self.send_text_submenu_right = send_menu_right.addMenu(s["send_text_submenu"])
        right_menu.addSeparator()
        right_menu.addAction(s["check_updates"], self.update_git)
        if restart:
            right_menu.addAction(s["restart"], self.restart_application)
        right_menu.addAction(s["toggle_visibility"], self.toggle_visible)
        right_menu.addSeparator()
        if not no_quit:
            right_menu.addAction(s["quit"], QtWidgets.QApplication.quit)
        self.tray.setContextMenu(right_menu)
        self.tray.activated.connect(self.handle_tray_activated)
        self.tray.show()

        # LEFT MENU
        self.left_menu = QtWidgets.QMenu()
        self.left_menu.addAction(s["launch_app"], self.start_app_launcher)
        self.left_menu.addAction(s["search_files"], self.start_file_search)
        self.left_menu.addAction(s["search_web"], self.start_web_search)
        self.left_menu.addSeparator()
        send_menu_left = self.left_menu.addMenu(s["send_menu"])
        self.send_files_submenu_left = send_menu_left.addMenu(s["send_files_submenu"])
        self.send_text_submenu_left = send_menu_left.addMenu(s["send_text_submenu"])
        
        self.update_peer_menus()

        # always on top timer
        self.stay_on_top_timer = QtCore.QTimer(self)
        self.stay_on_top_timer.timeout.connect(self.ensure_on_top)
        self.stay_on_top_timer.start(1000)

        # Super key
        self.show_menu_signal.connect(self.show_menu)
        self.start_hotkey_listener()

    def show_menu(self):
        self.left_menu.popup(QtGui.QCursor.pos())

    def on_press(self, key):
        if self.super_menu:
            if key == keyboard.Key.cmd:
                self.show_menu_signal.emit()

    def start_hotkey_listener(self):
        self.listener = keyboard.Listener(on_press=self.on_press)
        self.listener.start()

    def closeEvent(self, event):
        self.listener.stop()
        super().closeEvent(event)

    def ensure_on_top(self):
        if self.isVisible():
            self.raise_()

    def showEvent(self, event):
        super().showEvent(event)
        self.raise_()

    def mousePressEvent(self, event: QtGui.QMouseEvent):
        if event.button() == QtCore.Qt.LeftButton:                      #type: ignore
            self.left_menu.popup(event.globalPosition().toPoint())

        elif event.button() == QtCore.Qt.RightButton:                   #type: ignore
            self.tray.contextMenu().popup(event.globalPosition().toPoint())

    def handle_tray_activated(self, reason):
        if reason == QtWidgets.QSystemTrayIcon.ActivationReason.Trigger:
            self.left_menu.popup(QtGui.QCursor.pos())

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def update_peer_menus(self):
        self.send_files_submenu_left.clear()
        self.send_text_submenu_left.clear()
        self.send_files_submenu_right.clear()
        self.send_text_submenu_right.clear()
        
        no_peers_str = self.strings["main_window"]["no_peers"]

        peers = list(self.dukto_handler.peers.values())

        if not peers:
            no_peers_action_left_files = self.send_files_submenu_left.addAction(no_peers_str)
            no_peers_action_left_files.setEnabled(False)
            no_peers_action_left_text = self.send_text_submenu_left.addAction(no_peers_str)
            no_peers_action_left_text.setEnabled(False)
            
            no_peers_action_right_files = self.send_files_submenu_right.addAction(no_peers_str)
            no_peers_action_right_files.setEnabled(False)
            no_peers_action_right_text = self.send_text_submenu_right.addAction(no_peers_str)
            no_peers_action_right_text.setEnabled(False)
            return

        for peer in sorted(peers, key=lambda p: p.signature):
            file_action_left = self.send_files_submenu_left.addAction(peer.signature)
            file_action_right = self.send_files_submenu_right.addAction(peer.signature)
            
            text_action_left = self.send_text_submenu_left.addAction(peer.signature)
            text_action_right = self.send_text_submenu_right.addAction(peer.signature)

            file_action_left.triggered.connect(lambda checked=False, p=peer: self.start_file_send(p))
            file_action_right.triggered.connect(lambda checked=False, p=peer: self.start_file_send(p))
            
            text_action_left.triggered.connect(lambda checked=False, p=peer: self.start_text_send(p))
            text_action_right.triggered.connect(lambda checked=False, p=peer: self.start_text_send(p))

    def start_file_send(self, peer: Peer):
        dialog_title = self.strings["send_files_dialog_title"].format(peer_signature=peer.signature)
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            dialog_title,
            str(Path.home()),
        )
        if file_paths:
            self.dukto_handler.send_file(peer.address, file_paths, peer.port)

    def start_text_send(self, peer: Peer):
        dialog_title = self.strings["send_text_dialog_title"].format(peer_signature=peer.signature)
        dialog_label = self.strings["send_text_dialog_label"]
        text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self,
            dialog_title,
            dialog_label
        )
        if ok and text:
            self.dukto_handler.send_text(peer.address, text, peer.port)

    def show_receive_confirmation(self, sender_ip: str):
        reply = QtWidgets.QMessageBox.question(
            self,
            self.strings["receive_confirm_title"],
            self.strings["receive_confirm_text"].format(sender_ip=sender_ip),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.dukto_handler.approve_transfer()
        else:
            self.dukto_handler.reject_transfer()

    @QtCore.Slot(str)
    def handle_receive_start(self, sender_ip: str):
        s = self.strings["progress_dialog"]
        self.progress_dialog = QtWidgets.QProgressDialog(s["receiving_label"], s["cancel_button"], 0, 100, self)
        self.progress_dialog.setWindowTitle(s["receiving_title"].format(sender_ip=sender_ip))
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal) # type: ignore
        self.progress_dialog.show()
    
    @QtCore.Slot(str)
    def handle_send_start(self, dest_ip: str):
        s = self.strings["progress_dialog"]
        self.progress_dialog = QtWidgets.QProgressDialog(s["sending_label"], s["cancel_button"], 0, 100, self)
        self.progress_dialog.setWindowTitle(s["sending_title"].format(dest_ip=dest_ip))
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal) # type: ignore
        self.progress_dialog.show()

    @QtCore.Slot(int, int)
    def update_progress_dialog(self, total_size: int, received: int):
        if self.progress_dialog:
            self.progress_dialog.setMaximum(total_size)
            self.progress_dialog.setValue(received)

    @QtCore.Slot(list, int)
    def handle_receive_complete(self, received_files: list, total_size: int):
        if self.progress_dialog:
            self.progress_dialog.setValue(total_size)
            self.progress_dialog.close()
            self.progress_dialog = None
        
        QtWidgets.QMessageBox.information(self, self.strings["receive_complete_title"], self.strings["receive_complete_text"].format(count=len(received_files)))
        
        reply = QtWidgets.QMessageBox.question(
            self,
            self.strings["open_folder_title"],
            self.strings["open_folder_text"],
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.Yes
        )

        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            receive_dir = str(Path.home() / "Received")
            url = QtCore.QUrl.fromLocalFile(receive_dir)
            QtGui.QDesktopServices.openUrl(url)
    
    @QtCore.Slot(list)
    def handle_send_complete(self, sent_files: list):
        if self.progress_dialog:
            if self.progress_dialog.maximum() > 0:
                self.progress_dialog.setValue(self.progress_dialog.maximum())
            self.progress_dialog.close()
            self.progress_dialog = None
        
        if sent_files and sent_files[0] == "___DUKTO___TEXT___":
            QtWidgets.QMessageBox.information(self, self.strings["send_complete_title"], self.strings["send_complete_text_single"])
        else:
            QtWidgets.QMessageBox.information(self, self.strings["send_complete_title"], self.strings["send_complete_text"].format(count=len(sent_files)))

    @QtCore.Slot(str, int)
    def handle_receive_text(self, text: str, total_size: int):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        
        dialog = TextViewerDialog(text, self.strings, self)
        dialog.exec()

    @QtCore.Slot(str)
    def handle_dukto_error(self, error_msg: str):
        if self.progress_dialog:
            self.progress_dialog.close()
            self.progress_dialog = None
        QtWidgets.QMessageBox.critical(self, self.strings["dukto_error_title"], self.strings["dukto_error_text"].format(error_msg=error_msg))

    def start_app_launcher(self):
        self.app_launcher_dialog = AppLauncherDialog(self.strings, self)
        self.app_launcher_dialog.move(QtGui.QCursor.pos())
        self.app_launcher_dialog.show()

    def start_file_search(self):
        s = self.strings["file_search"]
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle(s["input_title"])
        dialog.setLabelText(s["input_label"])
        dialog.move(QtGui.QCursor.pos())
        
        ok = dialog.exec()
        pattern = dialog.textValue()
        
        if ok and pattern:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
                results = find(pattern, root='~')
            except RuntimeError as e:
                QtWidgets.QMessageBox.critical(self, s["search_error_title"], s["search_error_text"].format(e=e))
                return
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

            if results:
                self.results_dialog = FileSearchResults(results, self.strings, self)
                self.results_dialog.show()
            else:
                reply = QtWidgets.QMessageBox.question(self, s["no_results_title"], s["no_results_home_text"],
                                                       QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # type: ignore
                        results = find(pattern, root='/')
                    except RuntimeError as e:
                        QtWidgets.QMessageBox.critical(self, s["search_error_title"], s["search_error_text"].format(e=e))
                        return
                    finally:
                        QtWidgets.QApplication.restoreOverrideCursor()

                    if results:
                        self.results_dialog = FileSearchResults(results, self.strings, self)
                        self.results_dialog.show()
                    else:
                        QtWidgets.QMessageBox.information(self, s["no_results_title"], s["no_results_root_text"])

    def start_web_search(self):
        s = self.strings["web_search"]
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle(s["input_title"])
        dialog.setLabelText(s["input_label"])
        dialog.move(QtGui.QCursor.pos())

        ok = dialog.exec()
        query = dialog.textValue()
        
        if ok and query:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
                leta = MullvadLetaWrapper(engine="brave")
                results = leta.search(query)
                
                if results and results.get('results'):
                    self.web_results_dialog = WebSearchResults(results, self.strings, self)
                    self.web_results_dialog.show()
                else:
                    QtWidgets.QMessageBox.information(self, s["no_results_title"], s["no_results_text"])
                    
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, s["search_error_title"], s["search_error_text"].format(e=e))
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

    def update_git(self):
        s = self.strings["main_window"]["updater"]

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
        update_available = is_update_available()
        QtWidgets.QApplication.restoreOverrideCursor()

        if not update_available:
            QtWidgets.QMessageBox.information(self, s["no_updates_title"], s["no_updates_text"])
            return
        else:
            reply = QtWidgets.QMessageBox.question(self, s["update_available_title"],
                                                   s["update_available_text"],
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.Yes)
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return

        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
        status, message = update_repository()
        QtWidgets.QApplication.restoreOverrideCursor()
        
        if status == "UPDATED":
            reply = QtWidgets.QMessageBox.question(self, s["update_success_title"],
                                                   s["update_success_text"].format(message=message),
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.Yes)
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.restart_application()
            
        elif status == "FAILED":
            QtWidgets.QMessageBox.critical(self, s["update_failed_title"], s["update_failed_text"].format(message=message))

    def restart_application(self):
        presence.end()
        self.dukto_handler.shutdown()
        
        args = [sys.executable] + sys.argv

        subprocess.Popen(args)
        
        QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    try:
        with open(STRINGS_PATH, 'r', encoding='utf-8') as f:
            strings = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        print(f"Error loading strings file: {e}")
        error_dialog = QtWidgets.QMessageBox()
        error_dialog.setIcon(QtWidgets.QMessageBox.Critical) #type: ignore
        error_dialog.setText(f"Could not load required strings file from:\n{STRINGS_PATH}")
        error_dialog.setWindowTitle("Fatal Error")
        error_dialog.exec()
        sys.exit(1)

    restart = "--restart" in sys.argv
    no_quit = "--no-quit" in sys.argv
    super_menu = not "--no-super" in sys.argv
    
    dukto_handler = DuktoProtocol()
    
    pet = MainWindow(dukto_handler=dukto_handler, strings=strings, restart=restart, no_quit=no_quit, super_menu=super_menu)
    
    presence.start()
    
    dukto_handler.initialize()
    dukto_handler.say_hello()
    
    # bottom right corner
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)

    pet.show()

    app.aboutToQuit.connect(presence.end)
    app.aboutToQuit.connect(dukto_handler.shutdown)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()