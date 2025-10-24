#!/usr/bin/python3
import sys, os, subprocess, threading
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets
from pynput import keyboard

from core.file_search import find
from core.web_search import MullvadLetaWrapper
from core.discord_presence import presence
from core.app_launcher import list_apps, launch
from core.updater import update_repository, is_update_available
from core.dukto import DuktoProtocol

ASSET = Path(__file__).parent / "assets" / "2ktan.png"

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


class ReceiveConfirmationDialog(QtWidgets.QDialog):
    def __init__(self, sender_ip, file_count, total_size, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Incoming Transfer")
        
        size_mb = total_size / (1024 * 1024)
        
        layout = QtWidgets.QVBoxLayout()
        
        message = (
            f"Incoming transfer request from {sender_ip}\n\n"
            f"Files: {file_count}\n"
            f"Total size: {size_mb:.2f} MB\n\n"
            "Do you want to accept?"
        )
        
        label = QtWidgets.QLabel(message)
        layout.addWidget(label)
        
        button_box = QtWidgets.QDialogButtonBox(
            QtWidgets.QDialogButtonBox.StandardButton.Yes | QtWidgets.QDialogButtonBox.StandardButton.No
        )
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        
        layout.addWidget(button_box)
        self.setLayout(layout)


class MainWindow(QtWidgets.QMainWindow):
    show_menu_signal = QtCore.Signal()

    def __init__(self, dukto_handler, restart=False, no_quit=False, super_menu=True):
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
        self.dukto_handler = dukto_handler
        self.dukto_handler.on_receive_request = self.handle_receive_request
        
        self.receive_confirmation_event = threading.Event()
        self.receive_confirmation_result = [False]

        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))

        # RIGHT MENU
        right_menu = QtWidgets.QMenu()
        right_menu.addAction("Launch App", self.start_app_launcher)
        right_menu.addAction("Search Files", self.start_file_search)
        right_menu.addAction("Search Web", self.start_web_search)
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

    @QtCore.Slot(str, int, int)
    def show_receive_dialog(self, sender_ip, file_count, total_size):
        dialog = ReceiveConfirmationDialog(sender_ip, file_count, total_size, self)
        result = dialog.exec()
        
        self.receive_confirmation_result[0] = (result == QtWidgets.QDialog.Accepted)
        self.receive_confirmation_event.set()

    def handle_receive_request(self, sender_ip, file_count, total_size) -> bool:
        self.receive_confirmation_event.clear()
        
        QtCore.QMetaObject.invokeMethod(
            self, "show_receive_dialog", QtCore.Qt.QueuedConnection, #type: ignore
            QtCore.Q_ARG(str, sender_ip),
            QtCore.Q_ARG(int, file_count),
            QtCore.Q_ARG(int, total_size),
        )
        
        self.receive_confirmation_event.wait()
        return self.receive_confirmation_result[0]

    def restart_application(self):
        presence.end()
        self.dukto_handler.shutdown()
        
        args = [sys.executable] + sys.argv

        subprocess.Popen(args)
        
        QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    restart = "--restart" in sys.argv
    no_quit = "--no-quit" in sys.argv
    super_menu = not "--no-super" in sys.argv
    
    dukto_handler = DuktoProtocol()
    
    pet = MainWindow(dukto_handler=dukto_handler, restart=restart, no_quit=no_quit, super_menu=super_menu)
    
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