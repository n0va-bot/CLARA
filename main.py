#!/usr/bin/python3
import sys, os, subprocess
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

class DuktoDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("LAN Transfer (Dukto)")
        self.setMinimumSize(600, 400)

        # Dukto Protocol Backend
        self.protocol = DuktoProtocol()
        self.setup_callbacks()

        # UI Elements
        self.peer_list_widget = QtWidgets.QListWidget()
        self.send_file_button = QtWidgets.QPushButton("Send File(s)")
        self.send_text_button = QtWidgets.QPushButton("Send Text")
        self.refresh_button = QtWidgets.QPushButton("Refresh")
        self.progress_bar = QtWidgets.QProgressBar()
        
        # Layout
        layout = QtWidgets.QVBoxLayout(self)
        layout.addWidget(QtWidgets.QLabel("Discovered Peers:"))
        layout.addWidget(self.peer_list_widget)

        button_layout = QtWidgets.QHBoxLayout()
        button_layout.addWidget(self.refresh_button)
        button_layout.addStretch()
        button_layout.addWidget(self.send_text_button)
        button_layout.addWidget(self.send_file_button)
        layout.addLayout(button_layout)
        layout.addWidget(self.progress_bar)

        self.progress_bar.hide()

        # Connect signals
        self.refresh_button.clicked.connect(self.refresh_peers)
        self.send_file_button.clicked.connect(self.send_files)
        self.send_text_button.clicked.connect(self.send_text)

        # Initialize Dukto
        self.protocol.initialize()
        self.refresh_peers()

    def setup_callbacks(self):
        self.protocol.on_peer_added = self.add_peer
        self.protocol.on_peer_removed = self.remove_peer
        self.protocol.on_receive_start = lambda ip: self.show_progress()
        self.protocol.on_transfer_progress = self.update_progress
        self.protocol.on_receive_text = self.handle_received_text
        self.protocol.on_receive_complete = self.handle_receive_complete
        self.protocol.on_send_complete = lambda files: self.progress_bar.hide()
        self.protocol.on_error = self.handle_error

    @QtCore.Slot(Peer)
    def add_peer(self, peer: Peer):
        # Check if peer already exists
        for i in range(self.peer_list_widget.count()):
            item = self.peer_list_widget.item(i)
            if item.data(QtCore.Qt.UserRole).address == peer.address: # type: ignore
                return

        item = QtWidgets.QListWidgetItem(f"{peer.signature} ({peer.address})")
        item.setData(QtCore.Qt.UserRole, peer) # type: ignore
        self.peer_list_widget.addItem(item)

    @QtCore.Slot(Peer)
    def remove_peer(self, peer: Peer):
        for i in range(self.peer_list_widget.count()):
            item = self.peer_list_widget.item(i)
            if item and item.data(QtCore.Qt.UserRole).address == peer.address: # type: ignore
                self.peer_list_widget.takeItem(i)
                break

    def refresh_peers(self):
        self.peer_list_widget.clear()
        self.protocol.peers.clear()
        self.protocol.say_hello()

    def get_selected_peer(self) -> Peer | None:
        selected_items = self.peer_list_widget.selectedItems()
        if not selected_items:
            QtWidgets.QMessageBox.warning(self, "No Peer Selected", "Please select a peer from the list.")
            return None
        return selected_items[0].data(QtCore.Qt.UserRole) # type: ignore

    def send_files(self):
        peer = self.get_selected_peer()
        if not peer:
            return

        files, _ = QtWidgets.QFileDialog.getOpenFileNames(self, "Select Files to Send")
        if files:
            self.show_progress()
            self.protocol.send_file(peer.address, files, peer.port)

    def send_text(self):
        peer = self.get_selected_peer()
        if not peer:
            return

        text, ok = QtWidgets.QInputDialog.getMultiLineText(self, "Send Text", "Enter text to send:")
        if ok and text:
            self.show_progress()
            self.protocol.send_text(peer.address, text, peer.port)

    def show_progress(self):
        self.progress_bar.setValue(0)
        self.progress_bar.show()

    @QtCore.Slot(int, int)
    def update_progress(self, total_size, transferred):
        if total_size > 0:
            percentage = int((transferred / total_size) * 100)
            self.progress_bar.setValue(percentage)

    @QtCore.Slot(str, int)
    def handle_received_text(self, text, size):
        self.progress_bar.hide()
        QtWidgets.QMessageBox.information(self, "Text Received", text)

    @QtCore.Slot(list, int)
    def handle_receive_complete(self, files, size):
        self.progress_bar.hide()
        msg = f"Received {len(files)} file(s) successfully.\nThey are located in the application's directory."
        QtWidgets.QMessageBox.information(self, "Transfer Complete", msg)

    @QtCore.Slot(str)
    def handle_error(self, error_message):
        self.progress_bar.hide()
        QtWidgets.QMessageBox.critical(self, "Transfer Error", error_message)

    def closeEvent(self, event):
        self.protocol.shutdown()
        super().closeEvent(event)


class AppLauncherDialog(QtWidgets.QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("App Launcher")
        self.setMinimumSize(600, 400)
        
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        
        # Search box
        self.search_box = QtWidgets.QLineEdit()
        self.search_box.setPlaceholderText("Search applications...")
        self.search_box.textChanged.connect(self.filter_apps)
        layout.addWidget(self.search_box)
        
        # Apps list widget
        self.list_widget = QtWidgets.QListWidget()
        self.list_widget.itemClicked.connect(self.launch_app)
        layout.addWidget(self.list_widget)
        
        # Buttons
        button_layout = QtWidgets.QHBoxLayout()
        close_button = QtWidgets.QPushButton("Close")
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
            QtWidgets.QMessageBox.critical(self, "Error", f"Failed to load applications: {e}")
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
                QtWidgets.QMessageBox.critical(self, "Launch Error", 
                                              f"Failed to launch {app.name}: {e}")


class FileSearchResults(QtWidgets.QDialog):
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Search Results")
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
    def __init__(self, results, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Web Search Results - {results['query']}")
        self.setMinimumSize(800, 600)
        
        self.results = results
        
        # Main layout
        layout = QtWidgets.QVBoxLayout()
        
        # Info label
        info_text = f"Engine: {results['engine']} | Page: {results['page']}"
        if results.get('cached'):
            info_text += " | (Cached results)"
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
            news_label = QtWidgets.QLabel("News")
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
            prev_button = QtWidgets.QPushButton("← Previous Page")
            prev_button.clicked.connect(lambda: self.load_page(results['page'] - 1))
            nav_layout.addWidget(prev_button)
        
        nav_layout.addStretch()
        
        if results.get('has_next_page'):
            next_button = QtWidgets.QPushButton("Next Page →")
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
            new_dialog = WebSearchResults(new_results, self.parent())
            new_dialog.show()
            self.close()
            
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
        finally:
            QtWidgets.QApplication.restoreOverrideCursor()


class MainWindow(QtWidgets.QMainWindow):
    show_menu_signal = QtCore.Signal()

    def __init__(self, restart=False, no_quit=False, super_menu=True):
        super().__init__()

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

        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))

        # RIGHT MENU
        right_menu = QtWidgets.QMenu()
        right_menu.addAction("Launch App", self.start_app_launcher)
        right_menu.addAction("Search Files", self.start_file_search)
        right_menu.addAction("Search Web", self.start_web_search)
        right_menu.addAction("LAN Transfer (Dukto)", self.start_dukto)
        right_menu.addSeparator()
        right_menu.addAction("Check for updates", self.update_git)
        if restart:
            right_menu.addAction("Restart", self.restart_application)
        right_menu.addAction("Hide/Show", self.toggle_visible)
        right_menu.addSeparator()
        if not no_quit:
            right_menu.addAction("Quit", QtWidgets.QApplication.quit)
        self.tray.setContextMenu(right_menu)
        self.tray.activated.connect(self.handle_tray_activated)
        self.tray.show()

        # LEFT MENU
        self.left_menu = QtWidgets.QMenu()
        self.left_menu.addAction("Launch App", self.start_app_launcher)
        self.left_menu.addAction("Search Files", self.start_file_search)
        self.left_menu.addAction("Search Web", self.start_web_search)
        self.left_menu.addAction("LAN Transfer (Dukto)", self.start_dukto)

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

    def start_app_launcher(self):
        self.app_launcher_dialog = AppLauncherDialog(self)
        self.app_launcher_dialog.move(QtGui.QCursor.pos())
        self.app_launcher_dialog.show()

    def start_dukto(self):
        self.dukto_dialog = DuktoDialog(self)
        self.dukto_dialog.move(QtGui.QCursor.pos())
        self.dukto_dialog.show()

    def start_file_search(self):
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle("File Search")
        dialog.setLabelText("Enter search pattern:")
        dialog.move(QtGui.QCursor.pos())
        
        ok = dialog.exec()
        pattern = dialog.textValue()
        
        if ok and pattern:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
                results = find(pattern, root='~')
            except RuntimeError as e:
                QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
                return
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

            if results:
                self.results_dialog = FileSearchResults(results, self)
                self.results_dialog.show()
            else:
                reply = QtWidgets.QMessageBox.question(self, "No Results", "Sorry, I couldn't find anything in your home folder. Would you like me to search the root folder?",
                                                       QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No, QtWidgets.QMessageBox.StandardButton.No)
                if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                    try:
                        QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor)  # type: ignore
                        results = find(pattern, root='/')
                    except RuntimeError as e:
                        QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
                        return
                    finally:
                        QtWidgets.QApplication.restoreOverrideCursor()

                    if results:
                        self.results_dialog = FileSearchResults(results, self)
                        self.results_dialog.show()
                    else:
                        QtWidgets.QMessageBox.information(self, "No Results", "Sorry, I couldn't find anything in the root folder either.")

    def start_web_search(self):
        dialog = QtWidgets.QInputDialog(self)
        dialog.setWindowTitle("Web Search")
        dialog.setLabelText("Enter search query:")
        dialog.move(QtGui.QCursor.pos())

        ok = dialog.exec()
        query = dialog.textValue()
        
        if ok and query:
            try:
                QtWidgets.QApplication.setOverrideCursor(QtCore.Qt.WaitCursor) #type: ignore
                leta = MullvadLetaWrapper(engine="brave")
                results = leta.search(query)
                
                if results and results.get('results'):
                    self.web_results_dialog = WebSearchResults(results, self)
                    self.web_results_dialog.show()
                else:
                    QtWidgets.QMessageBox.information(self, "No Results", "No web search results found.")
                    
            except Exception as e:
                QtWidgets.QMessageBox.critical(self, "Search Error", str(e))
            finally:
                QtWidgets.QApplication.restoreOverrideCursor()

    def update_git(self):
        update_available = is_update_available()

        if not update_available:
            QtWidgets.QMessageBox.information(self, "No Updates", "You are already on the latest version.")
            return
        else:
            reply = QtWidgets.QMessageBox.question(self, "Update Available",
                                                   "An update is available. Would you like to download and install it now?",
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.Yes)
            if reply == QtWidgets.QMessageBox.StandardButton.No:
                return

        status, message = update_repository()
        
        if status == "UPDATED":
            reply = QtWidgets.QMessageBox.question(self, "Update Successful",
                                                   f"{message}\n\nWould you like to restart now to apply the changes?",
                                                   QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
                                                   QtWidgets.QMessageBox.StandardButton.Yes)
            if reply == QtWidgets.QMessageBox.StandardButton.Yes:
                self.restart_application()
            
        elif status == "FAILED":
            QtWidgets.QMessageBox.critical(self, "Update Failed", message)

    def restart_application(self):
        presence.end()
        
        args = [sys.executable] + sys.argv

        subprocess.Popen(args)
        
        QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    restart = "--restart" in sys.argv
    no_quit = "--no-quit" in sys.argv
    super_menu = not "--no-super" in sys.argv
    pet = MainWindow(restart=restart, no_quit=no_quit, super_menu=super_menu)
    presence.start()
    
    # bottom right corner
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)

    pet.show()

    app.aboutToQuit.connect(presence.end)
    sys.exit(app.exec())


if __name__ == "__main__":
    main()