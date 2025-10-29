from PySide6 import QtCore, QtGui, QtWidgets
from pathlib import Path
import subprocess
from pynput import keyboard
import sys

from core.updater import update_repository, is_update_available
from core.discord_presence import presence
from core.dukto import Peer
from core.file_search import find
from core.web_search import MullvadLetaWrapper
from core.http_share import FileShareServer

from windows.app_launcher import AppLauncherDialog
from windows.file_search import FileSearchResults
from windows.web_results import WebSearchResults
from windows.text_viewer import TextViewerDialog
from windows.calculator import CalculatorDialog

ASSET = Path(__file__).parent.parent / "assets" / "2ktan.png"

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
    
    # HTTP share signals
    http_download_signal = QtCore.Signal(str, str)


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
        
        # HTTP file sharing
        self.http_share = FileShareServer(port=8080)
        self.http_share.on_download = lambda filename, ip: self.http_download_signal.emit(filename, ip)

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
        self.http_download_signal.connect(self.handle_http_download)

        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))
        
        self.build_menus()
        
        # always on top timer
        self.stay_on_top_timer = QtCore.QTimer(self)
        self.stay_on_top_timer.timeout.connect(self.ensure_on_top)
        self.stay_on_top_timer.start(1000)

        # Super key
        self.show_menu_signal.connect(self.show_menu)
        self.start_hotkey_listener()

    def build_menus(self):
        s = self.strings["main_window"]["right_menu"]

        # LEFT MENU (Main widget)
        self.left_menu = QtWidgets.QMenu()
        self.left_menu.addAction(s["launch_app"], self.start_app_launcher)
        self.left_menu.addAction(s["search_files"], self.start_file_search)
        self.left_menu.addAction(s["search_web"], self.start_web_search)
        self.left_menu.addAction(s.get("calculator", "Calculator"), self.start_calculator)
        self.left_menu.addSeparator()
        share_menu_left = self.left_menu.addMenu(s["share_menu"])
        self.share_files_submenu_left = share_menu_left.addMenu(s["share_files_submenu"])
        self.share_text_submenu_left = share_menu_left.addMenu(s["share_text_submenu"])
        self.stop_share_action_left = share_menu_left.addAction("Stop Browser Share", self.stop_browser_share)
        self.left_menu.addSeparator()

        # RIGHT MENU (Tray icon)
        right_menu = QtWidgets.QMenu()
        right_menu.addAction(s["launch_app"], self.start_app_launcher)
        right_menu.addAction(s["search_files"], self.start_file_search)
        right_menu.addAction(s["search_web"], self.start_web_search)
        right_menu.addAction(s.get("calculator", "Calculator"), self.start_calculator)
        right_menu.addSeparator()
        share_menu_right = right_menu.addMenu(s["share_menu"])
        self.share_files_submenu_right = share_menu_right.addMenu(s["share_files_submenu"])
        self.share_text_submenu_right = share_menu_right.addMenu(s["share_text_submenu"])
        self.stop_share_action_right = share_menu_right.addAction("Stop Browser Share", self.stop_browser_share)
        right_menu.addSeparator()
        right_menu.addAction(s["check_updates"], self.update_git)
        
        if "--restart" in sys.argv:
            right_menu.addAction(s["restart"], self.restart_application)
        right_menu.addAction(s["toggle_visibility"], self.toggle_visible)
        right_menu.addSeparator()
        if "--no-quit" not in sys.argv:
            right_menu.addAction(s["quit"], QtWidgets.QApplication.quit)
        
        self.tray.setContextMenu(right_menu)
        self.tray.activated.connect(self.handle_tray_activated)
        self.tray.show()
        
        self.update_peer_menus()
        self.update_share_menu_state()

    def update_share_menu_state(self):
        s_menu = self.strings["main_window"]["right_menu"]
        
        is_sharing = self.http_share.is_running()
        has_shared_files = bool(self.http_share.shared_files)
        has_shared_text = bool(self.http_share.shared_text)

        # Set visibility of stop action
        self.stop_share_action_left.setVisible(is_sharing)
        self.stop_share_action_right.setVisible(is_sharing)

        # Configure file share menus
        for menu in [self.share_files_submenu_left, self.share_files_submenu_right]:
            for action in menu.actions():
                if hasattr(action, 'is_browser_action'):
                    menu.removeAction(action)
            
            action_text = "Add File(s)..." if has_shared_files else s_menu["via_browser"]
            browser_action = menu.addAction(action_text)
            browser_action.is_browser_action = True
            browser_action.triggered.connect(self.start_file_share_browser)
            
            if any(not a.isSeparator() and not hasattr(a, 'is_browser_action') for a in menu.actions()):
                if not any(a.isSeparator() for a in menu.actions()):
                     menu.addSeparator()

        # Configure text share menus
        for menu in [self.share_text_submenu_left, self.share_text_submenu_right]:
            for action in menu.actions():
                if hasattr(action, 'is_browser_action'):
                    menu.removeAction(action)
            
            action_text = "Change Shared Text..." if has_shared_text else s_menu["via_browser"]
            browser_action = menu.addAction(action_text)
            browser_action.is_browser_action = True
            browser_action.triggered.connect(self.start_text_share_browser)

            if any(not a.isSeparator() and not hasattr(a, 'is_browser_action') for a in menu.actions()):
                if not any(a.isSeparator() for a in menu.actions()):
                    menu.addSeparator()


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
        if self.http_share.is_running():
            self.http_share.stop()
        super().closeEvent(event)

    def ensure_on_top(self):
        if self.isVisible() and not self.left_menu.isVisible() and not self.tray.contextMenu().isVisible():
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
            self.tray.contextMenu().popup(QtGui.QCursor.pos())

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def update_peer_menus(self):
        s_main = self.strings["main_window"]
        no_peers_str = s_main["no_peers"]
        
        peers = list(self.dukto_handler.peers.values())
        
        for menu in [self.share_files_submenu_left, self.share_files_submenu_right, self.share_text_submenu_left, self.share_text_submenu_right]:
            actions_to_remove = [a for a in menu.actions() if not a.isSeparator() and not hasattr(a, 'is_browser_action')]
            for action in actions_to_remove:
                menu.removeAction(action)
        
        if not peers:
            for menu in [self.share_files_submenu_left, self.share_files_submenu_right, self.share_text_submenu_left, self.share_text_submenu_right]:
                action = menu.addAction(no_peers_str)
                action.setEnabled(False)
        else:
            for peer in sorted(peers, key=lambda p: p.signature):
                for files_menu, text_menu in [(self.share_files_submenu_left, self.share_text_submenu_left), (self.share_files_submenu_right, self.share_text_submenu_right)]:
                    file_action = files_menu.addAction(peer.signature)
                    text_action = text_menu.addAction(peer.signature)
                    file_action.triggered.connect(lambda checked=False, p=peer: self.start_file_send(p))
                    text_action.triggered.connect(lambda checked=False, p=peer: self.start_text_send(p))
    
        self.update_share_menu_state()

    def start_file_send(self, peer: Peer):
        dialog_title = self.strings["main_window"]["send_files_dialog_title"].format(peer_signature=peer.signature)
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, dialog_title, str(Path.home()))
        if file_paths:
            self.dukto_handler.send_file(peer.address, file_paths, peer.port)

    def start_text_send(self, peer: Peer):
        dialog_title = self.strings["main_window"]["send_text_dialog_title"].format(peer_signature=peer.signature)
        dialog_label = self.strings["main_window"]["send_text_dialog_label"]
        text, ok = QtWidgets.QInputDialog.getMultiLineText(self, dialog_title, dialog_label)
        if ok and text:
            self.dukto_handler.send_text(peer.address, text, peer.port)
    
    def start_file_share_browser(self):
        s = self.strings["main_window"]
        is_adding = bool(self.http_share.shared_files)
        
        dialog_title = "Select files to add" if is_adding else s["share_browser_dialog_title"]
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(self, dialog_title, str(Path.home()))
        
        if not file_paths:
            return

        try:
            if is_adding:
                self.http_share.add_files(file_paths)
                self.tray.showMessage("Files Added", f"{len(file_paths)} file(s) added to the share.", QtWidgets.QSystemTrayIcon.Information, 2000) #type: ignore
            else:
                url = self.http_share.share_files(file_paths)
                main_text = s["share_browser_text_files"]
                info_text = s["share_browser_files_info"].format(count=len(file_paths))
                if not self.http_share.shared_text:
                    self._show_sharing_dialog(url, main_text, info_text)
            
            self.update_share_menu_state()

        except Exception as e:
            QtWidgets.QMessageBox.critical(self, s["share_error_title"], s["share_error_text"].format(error=str(e)))

    def start_text_share_browser(self):
        s = self.strings["main_window"]
        is_changing = bool(self.http_share.shared_text)
        
        text, ok = QtWidgets.QInputDialog.getMultiLineText(
            self, 
            s["share_text_browser_dialog_title"], 
            s["share_text_browser_dialog_label"],
            self.http_share.shared_text or ""
        )

        if not (ok and text):
            return

        try:
            url = self.http_share.share_text(text)
            if not is_changing:
                main_text = s["share_browser_text_text"]
                info_text = s["share_browser_text_info"]
                if not self.http_share.shared_files:
                    self._show_sharing_dialog(url, main_text, info_text)

            self.update_share_menu_state()
        except Exception as e:
            QtWidgets.QMessageBox.critical(self, s["share_error_title"], s["share_error_text"].format(error=str(e)))

    def stop_browser_share(self):
        s = self.strings["main_window"]
        if self.http_share.is_running():
            self.http_share.stop()
            self.tray.showMessage(s["sharing_stopped_title"], s["sharing_stopped_text"], QtWidgets.QSystemTrayIcon.Information, 2000) #type: ignore
        self.update_share_menu_state()

    def _show_sharing_dialog(self, url: str, main_text: str, info_text: str):
        s = self.strings["main_window"]
        msg = QtWidgets.QMessageBox(self)
        msg.setIcon(QtWidgets.QMessageBox.Information) #type: ignore
        msg.setWindowTitle(s["share_browser_title"])
        msg.setText(main_text)
        msg.setInformativeText(f"{s['share_browser_url']}:\n\n{url}\n\n{info_text}")
        
        copy_btn = msg.addButton(s["copy_url"], QtWidgets.QMessageBox.ActionRole) #type: ignore
        open_btn = msg.addButton(s["open_browser"], QtWidgets.QMessageBox.ActionRole) #type: ignore
        msg.addButton(QtWidgets.QMessageBox.Ok) #type: ignore
        
        msg.exec()
        
        clicked = msg.clickedButton()
        if clicked == copy_btn:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(url)
            self.tray.showMessage(s["url_copied_title"], s["url_copied_text"], QtWidgets.QSystemTrayIcon.Information, 2000) #type: ignore
        elif clicked == open_btn:
            QtGui.QDesktopServices.openUrl(QtCore.QUrl(url))

    @QtCore.Slot(str, str)
    def handle_http_download(self, filename: str, client_ip: str):
        s = self.strings["main_window"]
        self.tray.showMessage(
            s["download_notification_title"],
            s["download_notification_text"].format(filename=filename, ip=client_ip),
            QtWidgets.QSystemTrayIcon.Information, #type: ignore
            3000
        )

    def show_receive_confirmation(self, sender_ip: str):
        reply = QtWidgets.QMessageBox.question(
            self,
            self.strings["main_window"]["receive_confirm_title"],
            self.strings["main_window"]["receive_confirm_text"].format(sender_ip=sender_ip),
            QtWidgets.QMessageBox.StandardButton.Yes | QtWidgets.QMessageBox.StandardButton.No,
            QtWidgets.QMessageBox.StandardButton.No
        )
        if reply == QtWidgets.QMessageBox.StandardButton.Yes:
            self.dukto_handler.approve_transfer()
        else:
            self.dukto_handler.reject_transfer()

    @QtCore.Slot(str)
    def handle_receive_start(self, sender_ip: str):
        s = self.strings["main_window"]["progress_dialog"]
        self.progress_dialog = QtWidgets.QProgressDialog(s["receiving_label"], s["cancel_button"], 0, 100, self)
        self.progress_dialog.setWindowTitle(s["receiving_title"].format(sender_ip=sender_ip))
        self.progress_dialog.setWindowModality(QtCore.Qt.WindowModal) # type: ignore
        self.progress_dialog.show()
    
    @QtCore.Slot(str)
    def handle_send_start(self, dest_ip: str):
        s = self.strings["main_window"]["progress_dialog"]
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
        
        s = self.strings["main_window"]
        QtWidgets.QMessageBox.information(self, s["receive_complete_title"], s["receive_complete_text"].format(count=len(received_files)))
        
        reply = QtWidgets.QMessageBox.question(
            self,
            s["open_folder_title"],
            s["open_folder_text"],
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
        
        s = self.strings["main_window"]
        if sent_files and sent_files[0] == "___DUKTO___TEXT___":
            QtWidgets.QMessageBox.information(self, s["send_complete_title"], s["send_complete_text_single"])
        else:
            QtWidgets.QMessageBox.information(self, s["send_complete_title"], s["send_complete_text"].format(count=len(sent_files)))

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
        QtWidgets.QMessageBox.critical(self, self.strings["main_window"]["dukto_error_title"], self.strings["main_window"]["dukto_error_text"].format(error_msg=error_msg))

    def start_app_launcher(self):
        self.app_launcher_dialog = AppLauncherDialog(self.strings, self)
        self.app_launcher_dialog.move(QtGui.QCursor.pos())
        self.app_launcher_dialog.show()

    def start_calculator(self):
        self.calculator_dialog = CalculatorDialog(self.strings, self)
        self.calculator_dialog.move(QtGui.QCursor.pos())
        self.calculator_dialog.show()

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
        if self.http_share.is_running():
            self.http_share.stop()
        
        args = [sys.executable] + sys.argv

        subprocess.Popen(args)
        
        QtWidgets.QApplication.quit()