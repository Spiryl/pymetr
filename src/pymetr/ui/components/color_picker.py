from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QColor, QPainter, QPaintEvent, QMouseEvent, QIcon
from PySide6.QtWidgets import (QWidget, QColorDialog, QHBoxLayout, 
                              QPushButton, QToolButton, QLabel)

class ColorButton(QToolButton):
    """
    A button that displays and lets the user pick a color.
    """
    colorChanged = Signal(QColor)
    
    def __init__(self, color=None, parent=None):
        super().__init__(parent)
        self.setToolButtonStyle(Qt.ToolButtonTextBesideIcon)
        self.setFixedWidth(30)
        self.setFixedHeight(20)
        
        # Set initial color
        self._color = QColor("#FF8400") if color is None else QColor(color)
        
        # Set tooltip
        self.setToolTip("Click to change accent color")
        
        # Connect signals
        self.clicked.connect(self._on_clicked)
    
    def color(self):
        """Get the current color."""
        return self._color
    
    def setColor(self, color):
        """Set the current color."""
        if self._color != color:
            self._color = color
            self.update()  # Trigger repaint
            self.colorChanged.emit(color)
    
    def paintEvent(self, event):
        """Custom paint to show the color."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw the color square
        rect = self.rect().adjusted(2, 2, -2, -2)  # Smaller to leave margin
        painter.setPen(Qt.black)
        painter.setBrush(self._color)
        painter.drawRoundedRect(rect, 3, 3)
    
    def _on_clicked(self):
        """Show color dialog when clicked."""
        dialog = QColorDialog(self._color, self)
        dialog.setWindowTitle("Select Accent Color")
        dialog.setOption(QColorDialog.ShowAlphaChannel, False)
        
        # Show predefined colors - good theme accents
        dialog.setCustomColor(0, QColor("#FF8400").rgb())  # Orange (default)
        dialog.setCustomColor(1, QColor("#3D6AEC").rgb())  # Blue
        dialog.setCustomColor(2, QColor("#00A86B").rgb())  # Green
        dialog.setCustomColor(3, QColor("#D32F2F").rgb())  # Red
        dialog.setCustomColor(4, QColor("#9C27B0").rgb())  # Purple
        dialog.setCustomColor(5, QColor("#FF9800").rgb())  # Amber
        dialog.setCustomColor(6, QColor("#607D8B").rgb())  # Blue Grey
        dialog.setCustomColor(7, QColor("#795548").rgb())  # Brown
        
        if dialog.exec():
            self.setColor(dialog.selectedColor())


class ThemeButton(QToolButton):
    """
    A button that toggles between light and dark themes.
    """
    themeChanged = Signal(str)  # Emits the new theme name
    
    def __init__(self, theme="dark", parent=None):
        super().__init__(parent)
        self._theme = theme
        
        # Set up appearance
        self.setFixedSize(26, 20)
        self.setToolTip("Toggle between dark and light theme")
        
        # Update icon for current theme
        self._update_icon()
        
        # Connect signals
        self.clicked.connect(self._on_clicked)
    
    def theme(self):
        """Get the current theme."""
        return self._theme
    
    def setTheme(self, theme):
        """Set the current theme."""
        if self._theme != theme:
            self._theme = theme
            self._update_icon()
            self.themeChanged.emit(theme)
    
    def _update_icon(self):
        """Update button icon based on current theme."""
        # Simple approach for now - could use actual icons later
        if self._theme == "dark":
            self.setText("☀️")  # Sun emoji for light mode
        else:
            self.setText("🌙")  # Moon emoji for dark mode
    
    def _on_clicked(self):
        """Toggle theme when clicked."""
        new_theme = "light" if self._theme == "dark" else "dark"
        self.setTheme(new_theme)


class ColorPicker(QWidget):
    """
    A widget for picking accent colors and toggling themes.
    """
    colorChanged = Signal(QColor)
    themeChanged = Signal(str)
    
    def __init__(self, color=None, theme="dark", parent=None):
        super().__init__(parent)
        
        # Create layout
        layout = QHBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)
        
        # Add label
        self.label = QLabel("Theme:")
        layout.addWidget(self.label)
        
        # Add theme button
        self.themeButton = ThemeButton(theme, self)
        self.themeButton.themeChanged.connect(self.themeChanged)
        layout.addWidget(self.themeButton)
        
        # Add color button
        self.colorButton = ColorButton(color, self)
        self.colorButton.colorChanged.connect(self.colorChanged)
        layout.addWidget(self.colorButton)
        
        # Set layout
        self.setLayout(layout)
    
    def color(self):
        """Get the current color."""
        return self.colorButton.color()
    
    def setColor(self, color):
        """Set the current color."""
        self.colorButton.setColor(color)
        
    def theme(self):
        """Get the current theme."""
        return self.themeButton.theme()
    
    def setTheme(self, theme):
        """Set the current theme."""
        self.themeButton.setTheme(theme)