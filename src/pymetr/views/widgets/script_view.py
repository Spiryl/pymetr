from pathlib import Path
from typing import Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QPlainTextEdit,
    QFontComboBox, QComboBox, QStatusBar, 
    QWidget, QLabel, QTextEdit
)
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, 
    QFont, QTextCursor, QPainter, QTextFormat
)
from PySide6.QtCore import Qt, Signal, Slot, QRegularExpression, QRect, QSize

from pymetr.views.widgets.base import BaseWidget
from pymetr.core.logging import logger

class LineNumberArea(QWidget):
    """Widget for displaying line numbers."""
    
    def __init__(self, editor):
        super().__init__(editor)
        self.editor = editor

    def sizeHint(self):
        return QSize(self.editor.line_number_area_width(), 0)

    def paintEvent(self, event):
        self.editor.line_number_area_paint_event(event)

class PythonHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for Python code."""
    
    def __init__(self, document):
        super().__init__(document)
        self._rules = []
        self._setup_formats()
        self._initialize_rules()

    def _setup_formats(self):
        """Initialize text formats for different syntax elements."""
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
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]

        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self._rules.append((pattern, self.formats['keyword']))

        self._rules.extend([
            (QRegularExpression(r'\b[A-Za-z0-9_]+(?=\s*\()'), self.formats['function']),
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.formats['string']),
            (QRegularExpression(r'\'[^\'\\]*(\\.[^\'\\]*)*\''), self.formats['string']),
            (QRegularExpression(r'#[^\n]*'), self.formats['comment']),
            (QRegularExpression(r'\b\d+\b'), self.formats['number']),
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
    """Enhanced text editor for Python scripts."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self._setup_editor()
        
        # Line number area
        self.line_number_area = LineNumberArea(self)
        
        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        # Initial setup
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def _setup_editor(self):
        """Configure editor appearance and behavior."""
        font = QFont("Consolas", 11)
        self.setFont(font)
        
        self.setStyleSheet("""
            QPlainTextEdit {
                background-color: #1E1E1E;
                color: #D4D4D4;
                padding: 8px;
                selection-background-color: #264F78;
                selection-color: #D4D4D4;
            }
        """)
        
        self.setTabStopDistance(self.fontMetrics().horizontalAdvance(' ') * 4)
        self.setLineWrapMode(QPlainTextEdit.NoWrap)

    def line_number_area_width(self) -> int:
        digits = len(str(max(1, self.blockCount())))
        space = 3 + self.fontMetrics().horizontalAdvance('9') * digits
        return space

    def update_line_number_area_width(self, _):
        self.setViewportMargins(self.line_number_area_width(), 0, 0, 0)

    def update_line_number_area(self, rect, dy):
        if dy:
            self.line_number_area.scroll(0, dy)
        else:
            self.line_number_area.update(0, rect.y(), 
                self.line_number_area.width(), rect.height())

    def resizeEvent(self, event):
        super().resizeEvent(event)
        cr = self.contentsRect()
        self.line_number_area.setGeometry(QRect(cr.left(), cr.top(),
            self.line_number_area_width(), cr.height()))

    def line_number_area_paint_event(self, event):
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
                painter.setPen(QColor("#858585"))
                painter.drawText(0, int(top), self.line_number_area.width(), 
                    self.fontMetrics().height(),
                    Qt.AlignRight, number)

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            selection.format.setBackground(QColor("#282828"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

class ScriptView(BaseWidget):
    """Widget for editing Python test scripts."""
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        self.modified = False
        
        # Set up UI before setting model
        self._setup_ui()
        
        # Set model and connect to signals
        self.set_model(model_id)

    def _setup_ui(self):
        """Initialize the UI components."""
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
        self.font_combo.currentFontChanged.connect(self._change_font)
        settings_layout.addWidget(self.font_combo)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([str(s) for s in [8,9,10,11,12,14,16,18,20]])
        self.size_combo.setCurrentText("11")
        self.size_combo.currentTextChanged.connect(self._change_font_size)
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
        
        # Connect editor signals
        self.editor.textChanged.connect(self._handle_text_changed)

    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if prop == 'status':
            self.status_bar.showMessage(f"Status: {value}")
            self.editor.setReadOnly(value == "Running")
        elif prop == 'progress':
            if value is not None:
                self.status_bar.showMessage(f"Progress: {value:.1f}%")

    def _handle_text_changed(self):
        """Handle editor content changes."""
        if not self.model:
            return
            
        self.modified = True
        self.status_bar.showMessage("Modified")

    def _change_font(self, font: QFont):
        """Update editor font family."""
        current_font = self.editor.font()
        current_font.setFamily(font.family())
        self.editor.setFont(current_font)

    def _change_font_size(self, size_str: str):
        """Update editor font size."""
        try:
            size = int(size_str)
            current_font = self.editor.font()
            current_font.setPointSize(size)
            self.editor.setFont(current_font)
        except ValueError:
            pass

    def load_content(self):
        """Load script content from model."""
        if not self.model:
            return
            
        path = self.model.get_property('script_path')
        if path and Path(path).exists():
            try:
                content = Path(path).read_text(encoding='utf-8')
                self.editor.setPlainText(content)
                self.modified = False
                self.status_bar.showMessage(f"Loaded {path}")
            except Exception as e:
                logger.error(f"Error loading script: {e}")
                self.status_bar.showMessage(f"Error loading script: {str(e)}")

    def save_content(self) -> bool:
        """Save current content to file."""
        if not self.model:
            return False
            
        path = self.model.get_property('script_path')
        if not path:
            return False
            
        try:
            content = self.editor.toPlainText()
            Path(path).write_text(content, encoding='utf-8')
            self.modified = False
            self.status_bar.showMessage("Script saved successfully")
            return True
        except Exception as e:
            logger.error(f"Error saving script: {e}")
            self.status_bar.showMessage(f"Error saving script: {str(e)}")
            return False

    def has_unsaved_changes(self) -> bool:
        """Check if there are unsaved changes."""
        return self.modified
    
    def set_model(self, model_id: str):
        super().set_model(model_id)
        # You want to do something like:
        if self.model:
            self.load_content()