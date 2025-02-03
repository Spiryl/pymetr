# src/pymetr/views/widgets/script_view.py
from pathlib import Path
from typing import Optional
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QFontComboBox, QComboBox, QStatusBar, QTextEdit
)
from PySide6.QtGui import QSyntaxHighlighter, QTextCharFormat, QColor, QFont, QTextCursor, QPainter, QTextFormat
from PySide6.QtCore import Qt, QRegularExpression, QRect, QSize

from ...state import ApplicationState

class LineNumberArea(QWidget):
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code"""
    def __init__(self, document):
        super().__init__(document)
        self._rules = []  # Store the highlighting rules
        self._setup_formats()
        self._initialize_rules()

    def _setup_formats(self):
        """Initialize text formats for different syntax elements"""
        self.formats = {
            'keyword': self._create_format("#C586C0", True),     # Purple
            'builtin': self._create_format("#4EC9B0", True),     # Teal
            'function': self._create_format("#DCDCAA", False),   # Yellow
            'comment': self._create_format("#6A9955", False, True), # Green
            'string': self._create_format("#CE9178", False),     # Orange
            'number': self._create_format("#B5CEA8", False),     # Light green
            'decorator': self._create_format("#D7BA7D", False),  # Gold
        }

    def _create_format(self, color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _initialize_rules(self):
        """Setup syntax highlighting rules."""
        # Python keywords
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]

        # Add keyword rules
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self._rules.append((pattern, self.formats['keyword']))

        # Add other rules
        self._rules.extend([
            # Functions
            (QRegularExpression(r'\b[A-Za-z0-9_]+(?=\s*\()'), self.formats['function']),
            
            # Double-quoted strings
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.formats['string']),
            
            # Single-quoted strings
            (QRegularExpression(r'\'[^\'\\]*(\\.[^\'\\]*)*\''), self.formats['string']),
            
            # Comments
            (QRegularExpression(r'#[^\n]*'), self.formats['comment']),
            
            # Numbers
            (QRegularExpression(r'\b\d+\b'), self.formats['number']),
            
            # Decorators
            (QRegularExpression(r'@\w+'), self.formats['decorator']),
        ])

    def highlightBlock(self, text: str):
        """Apply highlighting to a block of text."""
        for pattern, format in self._rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), format)

class ScriptEditor(QPlainTextEdit):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setup_editor()
        
        # Create and set up line number area
        self.line_number_area = LineNumberArea(self)
        
        # Connect signals for line numbers
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        # Initial setup
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def setup_editor(self):
        """Configure editor appearance and behavior"""
        # Set default font
        font = QFont("Consolas", 11)
        self.setFont(font)
        
        # Set colors and styling
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                padding: 8px;
                selection-background-color: #264F78;
                selection-color: #D4D4D4;
            }
        """)
        
        # Editor settings
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def line_number_area_width(self):
        """Calculate the width needed for the line number area."""
        digits = 1
        max_num = max(1, self.blockCount())
        while max_num >= 10:
            max_num //= 10
            digits += 1
            
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, new_block_count):
        """Update the editor's viewport margins."""
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        """Handle scrolling of the line number area."""
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), 
                self.line_number_area.width(), rect.height())

        if rect.contains(self.viewport().rect()):
            self.update_line_number_area_width(0)

    def resizeEvent(self, event):
        """Handle resize events to adjust the line number area."""
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
        """Paint the line numbers."""
        painter = QPainter(self.line_number_area)
        painter.fillRect(event.rect(), QColor("#1E1E1E"))

        block = self.firstVisibleBlock()
        block_number = block.blockNumber()
        offset = self.contentOffset()
        top = self.blockBoundingGeometry(block).translated(offset).top()
        bottom = top + self.blockBoundingRect(block).height()

        while block.isValid() and top <= event.rect().bottom():
            if block.isVisible() and bottom >= event.rect().top():
                number = str(block_number + 1)
                painter.setPen(QColor("#858585"))  # Gray color for line numbers
                painter.drawText(0, int(top), self.line_number_area.width(), 
                    self.fontMetrics().height(),
                    Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        """Highlight the current line."""
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#282828"))  # Dark gray for current line
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

class ScriptView(QWidget):
    """Widget for editing Python test scripts"""
    def __init__(self, state: ApplicationState, model_id: str, parent: Optional[QWidget] = None):
        super().__init__(parent)
        self.state = state
        self.model_id = model_id
        self.model = self.state.registry.get_model(model_id)
        
        if not self.model:
            raise ValueError(f"No model found with ID: {model_id}")
            
        self.setup_ui()
        self.register_observers()
        self.load_content()

        # Connect to engine signals
        self.state.engine.script_started.connect(self._handle_script_started)
        self.state.engine.script_finished.connect(self._handle_script_finished)

    def setup_ui(self):
        """Initialize the UI components"""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Editor settings panel
        self.settings_panel = QWidget()
        settings_layout = QHBoxLayout(self.settings_panel)
        settings_layout.setContentsMargins(4, 4, 4, 4)
        
        # Font controls
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Consolas"))
        self.font_combo.currentFontChanged.connect(self.change_font)
        settings_layout.addWidget(self.font_combo)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([str(s) for s in [8,9,10,11,12,14,16,18,20]])
        self.size_combo.setCurrentText("11")
        self.size_combo.currentTextChanged.connect(self.change_font_size)
        settings_layout.addWidget(self.size_combo)
        
        settings_layout.addStretch()
        layout.addWidget(self.settings_panel)

        # Editor
        self.editor = ScriptEditor()
        self.highlighter = PythonHighlighter(self.editor.document())
        layout.addWidget(self.editor)
        
        # Status bar
        self.status_bar = QStatusBar()
        self.status_bar.setStyleSheet("""
            QStatusBar {
                background: #007ACC;
                color: white;
            }
        """)
        layout.addWidget(self.status_bar)

    def register_observers(self):
        """Register for state changes"""
        self.state.signals.connect(
            f"test.{self.model_id}.status",
            self.handle_test_status_changed
        )
        self.state.signals.connect(
            f"test.{self.model_id}.progress",
            self.handle_test_progress
        )

    def _handle_script_started(self, script_id: str):
        """Handle script execution start"""
        if script_id == self.model_id:
            self.editor.setReadOnly(True)
            self.status_bar.showMessage("Executing script...")

    def _handle_script_finished(self, script_id: str, success: bool, error_msg: str):
        """Handle script execution completion"""
        if script_id == self.model_id:
            self.editor.setReadOnly(False)
            if success:
                self.status_bar.showMessage("Script execution completed successfully")
            else:
                self.status_bar.showMessage(f"Script failed: {error_msg}")

    def handle_test_status_changed(self, payload: dict):
        """Handle test status updates"""
        new_status = payload["new_status"]
        self.status_bar.showMessage(f"TestScript Status: {new_status}")

    def handle_test_progress(self, payload: dict):
        """Handle test progress updates"""
        percent = payload["percent"]
        message = payload.get("message", "")
        self.status_bar.showMessage(f"Progress: {percent}% - {message}")

    def load_content(self):
        """Load script content from model"""
        if hasattr(self.model, 'script_path') and self.model.script_path:
            path = Path(self.model.script_path)
            if path.exists():
                try:
                    content = path.read_text(encoding='utf-8')
                    self.editor.setPlainText(content)
                    self.status_bar.showMessage(f"Loaded {path}")
                except Exception as e:
                    self.status_bar.showMessage(f"Error loading script: {str(e)}")

    def get_content(self) -> str:
        """Get current editor content"""
        return self.editor.toPlainText()

    def save_content(self) -> bool:
        """Save current content to file"""
        if not hasattr(self.model, 'script_path') or not self.model.script_path:
            return False
            
        try:
            content = self.get_content()
            self.model.script_path.write_text(content, encoding='utf-8')
            self.status_bar.showMessage("Script saved successfully")
            return True
        except Exception as e:
            self.status_bar.showMessage(f"Error saving script: {str(e)}")
            return False

    def change_font(self, font: QFont):
        """Update editor font family"""
        current_font = self.editor.font()
        current_font.setFamily(font.family())
        self.editor.setFont(current_font)

    def change_font_size(self, size_str: str):
        """Update editor font size"""
        try:
            size = int(size_str)
            current_font = self.editor.font()
            current_font.setPointSize(size)
            self.editor.setFont(current_font)
        except ValueError:
            pass