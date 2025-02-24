from typing import Optional
from PySide6.QtWidgets import (
    QVBoxLayout, QPlainTextEdit, QWidget, QTextEdit
)
from PySide6.QtGui import (
    QSyntaxHighlighter, QTextCharFormat, QColor, 
    QFont, QTextCursor, QPainter, QTextFormat
)
from PySide6.QtCore import Qt, Signal, QRect, QSize, QRegularExpression

from pymetr.ui.views.base import BaseWidget
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
    """
    Syntax highlighter for Python code with a bright, neon-inspired palette.
    Adjust as you see fit!
    """
    
    def __init__(self, document):
        super().__init__(document)
        self._rules = []
        self._setup_formats()
        self._initialize_rules()

    def _setup_formats(self):
        """Initialize text formats for different syntax elements."""
        # A bright/neon palette example:
        self.formats = {
            # Purple neon for keywords
            'keyword':   self._create_format("#9D00FF", bold=True),  
            # Electric cyan for builtins
            'builtin':   self._create_format("#5E57FF", bold=True),
            # Bright orange for functions
            'function':  self._create_format("#FF9535", bold=False),
            # Slightly subdued green for comments (italic)
            'comment':   self._create_format("#4BAA36", italic=True),
            # Neon yellow for strings
            'string':    self._create_format("#4BEE36", bold=False),
            # Gold for numbers
            'number':    self._create_format("#5E57FF", bold=False),
            # Neon pink for decorators
            'decorator': self._create_format("#F23CA6", bold=False),
        }

    def _create_format(self, color: str, bold: bool=False, italic: bool=False) -> QTextCharFormat:
        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        if bold:
            fmt.setFontWeight(QFont.Bold)
        if italic:
            fmt.setFontItalic(True)
        return fmt

    def _initialize_rules(self):
        """Setup syntax highlighting rules using regular expressions."""
        keywords = [
            'and', 'as', 'assert', 'break', 'class', 'continue', 'def',
            'del', 'elif', 'else', 'except', 'False', 'finally', 'for',
            'from', 'global', 'if', 'import', 'in', 'is', 'lambda',
            'None', 'nonlocal', 'not', 'or', 'pass', 'raise', 'return',
            'True', 'try', 'while', 'with', 'yield'
        ]

        # Mark keywords
        for word in keywords:
            pattern = QRegularExpression(r'\b' + word + r'\b')
            self._rules.append((pattern, self.formats['keyword']))

        # Additional patterns
        self._rules.extend([
            # Functions (sequence of word chars followed by parentheses)
            (QRegularExpression(r'\b[A-Za-z0-9_]+(?=\s*\()'), self.formats['function']),
            # Strings (double or single quoted)
            (QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), self.formats['string']),
            (QRegularExpression(r'\'[^\'\\]*(\\.[^\'\\]*)*\''), self.formats['string']),
            # Comments (#...)
            (QRegularExpression(r'#[^\n]*'), self.formats['comment']),
            # Numbers (simple integer pattern)
            (QRegularExpression(r'\b\d+\b'), self.formats['number']),
            # Decorators (@something)
            (QRegularExpression(r'@\w+'), self.formats['decorator']),
        ])

    def highlightBlock(self, text: str):
        """Apply highlighting to a block of text."""
        for pattern, fmt in self._rules:
            matches = pattern.globalMatch(text)
            while matches.hasNext():
                match = matches.next()
                self.setFormat(match.capturedStart(), match.capturedLength(), fmt)

class ScriptEditor(QPlainTextEdit):
    """Enhanced text editor for Python scripts."""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        
        # Line number area
        self.line_number_area = LineNumberArea(self)
        
        # Setup editor appearance
        self._setup_editor()
        
        # Connect signals
        self.blockCountChanged.connect(self.update_line_number_area_width)
        self.updateRequest.connect(self.update_line_number_area)
        self.cursorPositionChanged.connect(self.highlight_current_line)
        
        # Initial setup
        self.update_line_number_area_width(0)
        self.highlight_current_line()

    def _setup_editor(self):
        """Configure editor appearance and behavior."""
        # Set default font
        font = QFont("Consolas", 11)
        self.setFont(font)
        
        # Configure tab stops and wrapping
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
                painter.drawText(
                    0, int(top),
                    self.line_number_area.width(),
                    self.fontMetrics().height(),
                    Qt.AlignRight, number
                )

            block = block.next()
            top = bottom
            bottom = top + self.blockBoundingRect(block).height()
            block_number += 1

    def highlight_current_line(self):
        extra_selections = []

        if not self.isReadOnly():
            selection = QTextEdit.ExtraSelection()
            # A slightly lighter background to show the active line
            selection.format.setBackground(QColor("#282828"))
            selection.format.setProperty(QTextFormat.FullWidthSelection, True)
            selection.cursor = self.textCursor()
            selection.cursor.clearSelection()
            extra_selections.append(selection)

        self.setExtraSelections(extra_selections)

class ScriptView(BaseWidget):
    """Core widget for editing Python scripts."""
    
    content_changed = Signal()  # Emitted when text content changes
    
    def __init__(self, state, model_id: str, parent=None):
        super().__init__(state, parent)
        self._original_content = ""  # Store original content for modification checking
        self._setup_ui()
        self.set_model(model_id)

    def _setup_ui(self):
        """Initialize the core editor UI."""
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Core editor
        self.editor = ScriptEditor()
        self.highlighter = PythonHighlighter(self.editor.document())
        layout.addWidget(self.editor)
        
        # Connect editor signals
        self.editor.textChanged.connect(self.content_changed)

    def set_font(self, font: QFont):
        """Update editor font."""
        self.editor.setFont(font)

    def get_content(self) -> str:
        """Get current editor content."""
        return self.editor.toPlainText()

    def set_content(self, content: str):
        """Set editor content."""
        self.editor.setPlainText(content)

    def set_original_content(self, content: str):
        """Set the baseline content for modification checking."""
        self._original_content = content

    def has_unsaved_changes(self) -> bool:
        """Check if current content differs from original."""
        return self.get_content() != self._original_content

    def set_read_only(self, read_only: bool):
        """Set editor read-only state."""
        self.editor.setReadOnly(read_only)
