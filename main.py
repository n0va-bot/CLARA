#!/usr/bin/python3
import sys, os, subprocess
from pathlib import Path
from PySide6 import QtCore, QtGui, QtWidgets

from core.file_search import find
from core.web_search import MullvadLetaWrapper

ASSET = Path(__file__).parent / "assets" / "2ktan.png"

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
        """Opens the directory containing the selected file."""
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
        """Create widget for infobox display."""
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
        """Create widget for news item display."""
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
        """Create widget for search result display."""
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
        """Load a different page of results."""
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
    def __init__(self, restart=False):
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

        self.tray = QtWidgets.QSystemTrayIcon(self)
        self.tray.setIcon(QtGui.QIcon(str(ASSET)))

        # RIGHT MENU
        right_menu = QtWidgets.QMenu()
        right_menu.addAction("Search Files", self.start_file_search)
        right_menu.addAction("Search Web", self.start_web_search)
        right_menu.addSeparator()
        if restart:
            right_menu.addAction("Restart", self.restart_application)
        right_menu.addAction("Hide/Show", self.toggle_visible)
        right_menu.addSeparator()
        right_menu.addAction("Quit", QtWidgets.QApplication.quit)
        self.tray.setContextMenu(right_menu)
        self.tray.show()

        # LEFT MENU
        self.left_menu = QtWidgets.QMenu()
        self.left_menu.addAction("Search Files", self.start_file_search)
        self.left_menu.addAction("Search Web", self.start_web_search)

        # always on top timer
        self.stay_on_top_timer = QtCore.QTimer(self)
        self.stay_on_top_timer.timeout.connect(self.ensure_on_top)
        self.stay_on_top_timer.start(1000)

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

    def toggle_visible(self):
        self.setVisible(not self.isVisible())

    def start_file_search(self):
        pattern, ok = QtWidgets.QInputDialog.getText(self, "File Search", "Enter search pattern:")
        
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
        query, ok = QtWidgets.QInputDialog.getText(self, "Web Search", "Enter search query:")        
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

    def restart_application(self):
        """Restarts the application."""
        subprocess.Popen([sys.executable] + sys.argv)
        QtWidgets.QApplication.quit()


def main():
    app = QtWidgets.QApplication(sys.argv)
    app.setApplicationName("CLARA")

    restart_enabled = "--restart" in sys.argv
    pet = MainWindow(restart=restart_enabled)
    
    # bottom right corner
    screen_geometry = app.primaryScreen().availableGeometry()
    pet_geometry = pet.frameGeometry()
    x = screen_geometry.width() - pet_geometry.width()
    y = screen_geometry.height() - pet_geometry.height()
    pet.move(x, y)

    pet.show()

    sys.exit(app.exec())

if __name__ == "__main__":
    main()