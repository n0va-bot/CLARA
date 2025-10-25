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
        right_menu.addAction(s.get("calculator", "Calculator"), self.start_calculator)
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
        self.left_menu.addAction(s.get("calculator", "Calculator"), self.start_calculator)
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
        dialog_title = self.strings["main_window"]["send_files_dialog_title"].format(peer_signature=peer.signature)
        file_paths, _ = QtWidgets.QFileDialog.getOpenFileNames(
            self,
            dialog_title,
            str(Path.home()),
        )
        if file_paths:
            self.dukto_handler.send_file(peer.address, file_paths, peer.port)

    def start_text_send(self, peer: Peer):
        dialog_title = self.strings["main_window"]["send_text_dialog_title"].format(peer_signature=peer.signature)
        dialog_label = self.strings["main_window"]["send_text_dialog_label"]
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
        
        args = [sys.executable] + sys.argv

        subprocess.Popen(args)
        
        QtWidgets.QApplication.quit()