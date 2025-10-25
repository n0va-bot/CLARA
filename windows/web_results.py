from PySide6 import QtCore, QtWidgets
from core.web_search import MullvadLetaWrapper

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