from PySide6.QtWidgets import QWidget, QVBoxLayout, QTextBrowser

class HtmlView(QWidget):
    """A simple HTML-based view for reports and welcome messages"""
    def __init__(self, state, title, html_content, parent=None):
        super().__init__(parent)
        self.state = state
        self.title = title

        layout = QVBoxLayout(self)
        self.browser = QTextBrowser()
        self.browser.setHtml(html_content)
        layout.addWidget(self.browser)
