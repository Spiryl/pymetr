from pathlib import Path
from typing import Optional
import json

from PySide6.QtCore import QObject, QSettings, Signal
from PySide6.QtGui import QColor, QPalette
from PySide6.QtWidgets import QApplication

from pymetr.core.logging import logger

class ThemeService(QObject):
    """
    Service for theme management and accent colors.
    Provides a centralized API for all theme-related functionality.
    """
    
    # Signals
    theme_changed = Signal(str)  # Emitted when theme changes
    accent_color_changed = Signal(QColor)  # Emitted when accent color changes
    
    # Singleton instance
    _instance = None
    
    # Available themes
    AVAILABLE_THEMES = ["dark", "light"]
    
    # Default accent colors for each theme
    DEFAULT_ACCENT_COLORS = {
        "dark": "#FF8400",  # Orange
        "light": "#3D6AEC"  # Blue
    }
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of ThemeService."""
        if cls._instance is None:
            cls._instance = ThemeService()
        return cls._instance
    
    def __init__(self):
        """Initialize ThemeService."""
        super().__init__()
        
        self._settings = QSettings("PyMetr", "PyMetr")
        
        # Load current theme and accent color
        self._current_theme = self._settings.value("theme/current", "dark")
        if self._current_theme not in self.AVAILABLE_THEMES:
            self._current_theme = "dark"
            
        self._accent_color = QColor(self._settings.value(
            f"theme/{self._current_theme}/accentColor", 
            self.DEFAULT_ACCENT_COLORS[self._current_theme]
        ))
        
        # Cache for calculated theme values
        self._theme_cache = {}
        
    def get_current_theme(self) -> str:
        """Get the current theme name."""
        return self._current_theme
        
    def set_theme(self, theme_name: str) -> bool:
        """
        Set the current theme.
        
        Args:
            theme_name: Name of the theme to set
            
        Returns:
            True if successful, False otherwise
        """
        if theme_name not in self.AVAILABLE_THEMES:
            logger.warning(f"ThemeService: Unknown theme '{theme_name}'")
            return False
            
        if theme_name == self._current_theme:
            return True  # No change needed
            
        # Update current theme
        self._current_theme = theme_name
        self._settings.setValue("theme/current", theme_name)
        
        # Reset to default accent color for this theme if not set
        accent_key = f"theme/{theme_name}/accentColor"
        if not self._settings.contains(accent_key):
            self._accent_color = QColor(self.DEFAULT_ACCENT_COLORS[theme_name])
            self._settings.setValue(accent_key, self._accent_color.name())
        else:
            self._accent_color = QColor(self._settings.value(accent_key))
        
        # Clear cache
        self._theme_cache = {}
        
        # Emit signal
        self.theme_changed.emit(theme_name)
        self.accent_color_changed.emit(self._accent_color)
        
        return True
        
    def get_accent_color(self) -> QColor:
        """Get the current accent color."""
        return QColor(self._accent_color)
        
    def set_accent_color(self, color: QColor) -> bool:
        """
        Set the accent color for the current theme.
        
        Args:
            color: Color to set
            
        Returns:
            True if successful, False otherwise
        """
        if not color.isValid():
            logger.warning("ThemeService: Invalid color")
            return False
            
        self._accent_color = color
        self._settings.setValue(f"theme/{self._current_theme}/accentColor", color.name())
        
        # Clear cache
        self._theme_cache = {}
        
        # Emit signal
        self.accent_color_changed.emit(color)
        
        return True
    
    def get_stylesheet(self) -> str:
        """
        Get the stylesheet for the current theme with accent color applied.
        
        Returns:
            Complete stylesheet as string
        """
        try:
            # Check cache
            if "stylesheet" in self._theme_cache:
                return self._theme_cache["stylesheet"]
                
            # Look for the QSS file in the ui/styles directory
            stylesheet = ""
            
            try:
                # First approach: Try to import the styles module
                from pymetr.ui import styles as styles_module
                styles_dir = Path(styles_module.__file__).parent
                stylesheet_path = styles_dir / "main.qss"
                
                if stylesheet_path.exists():
                    logger.debug(f"ThemeService: Loading stylesheet from {stylesheet_path}")
                    with open(stylesheet_path, 'r') as f:
                        stylesheet = f.read()
                else:
                    logger.warning(f"ThemeService: Stylesheet file not found at {stylesheet_path}")
            except (ImportError, AttributeError, TypeError) as e:
                # Second approach: Try to find relative to the current file
                logger.debug(f"ThemeService: Could not import styles module, trying alternative path: {e}")
                try:
                    current_dir = Path(__file__).parent
                    ui_dir = current_dir.parent / "ui"
                    styles_dir = ui_dir / "styles"
                    stylesheet_path = styles_dir / "main.qss"
                    
                    if stylesheet_path.exists():
                        logger.debug(f"ThemeService: Loading stylesheet from {stylesheet_path}")
                        with open(stylesheet_path, 'r') as f:
                            stylesheet = f.read()
                    else:
                        logger.warning(f"ThemeService: Stylesheet file not found at {stylesheet_path}")
                except Exception as e2:
                    logger.warning(f"ThemeService: Alternative path also failed: {e2}")
            
            # If no stylesheet was loaded, use a fallback
            if not stylesheet:
                logger.warning("ThemeService: Using fallback stylesheet")
                stylesheet = """
                    QWidget {
                        background-color: #1e1e1e;
                        color: #f5f5f5;
                    }
                    /* Default fallback styling */
                """
            
            # Apply theme variables
            stylesheet = self._apply_theme_variables(stylesheet)
            
            # Cache result
            self._theme_cache["stylesheet"] = stylesheet
            
            return stylesheet
            
        except Exception as e:
            logger.error(f"ThemeService: Error loading stylesheet: {e}")
            # Return a minimal stylesheet to prevent infinite recursion
            return """
                QWidget {
                    background-color: #1e1e1e;
                    color: #f5f5f5;
                }
            """
    
    def apply_theme(self, app: QApplication) -> bool:
        """
        Apply the current theme to the application.
        
        Args:
            app: QApplication instance
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Get stylesheet
            stylesheet = self.get_stylesheet()
            
            # Debug: Save stylesheet to a file for inspection
            debug_path = Path("stylesheet_debug.qss")
            with open(debug_path, "w", encoding="utf-8") as f:
                f.write(stylesheet)
            logger.debug(f"ThemeService: Saved debug stylesheet to {debug_path}")
                
            # Apply to application - wrap in try/except to catch stylesheet errors
            try:
                app.setStyleSheet(stylesheet)
            except Exception as style_error:
                logger.error(f"ThemeService: Error applying stylesheet: {style_error}")
                
                # Try applying parts of the stylesheet to find the problematic section
                lines = stylesheet.split('\n')
                chunk_size = 50  # Process 50 lines at a time
                
                for i in range(0, len(lines), chunk_size):
                    chunk = '\n'.join(lines[i:i+chunk_size])
                    try:
                        app.setStyleSheet(chunk)
                        logger.debug(f"ThemeService: Chunk {i}-{i+chunk_size} applied successfully")
                    except Exception as e:
                        logger.error(f"ThemeService: Error in chunk {i}-{i+chunk_size}: {e}")
                        
                        # Try individual lines in the problematic chunk
                        for j, line in enumerate(lines[i:i+chunk_size]):
                            try:
                                app.setStyleSheet(line)
                            except Exception as e2:
                                logger.error(f"ThemeService: Error in line {i+j}: {line.strip()}")
                
                # Fall back to a minimal working stylesheet
                app.setStyleSheet("QWidget { background-color: #1e1e1e; color: #f5f5f5; }")
                
            # Update application palette
            self._apply_palette(app)
            
            return True
            
        except Exception as e:
            logger.error(f"ThemeService: Error applying theme: {e}")
            return False
    
    def _apply_theme_variables(self, stylesheet: str) -> str:
        """
        Apply theme colors directly to the stylesheet via string replacement.
        Since Qt doesn't fully support CSS variables, we'll directly substitute colors.
        
        Args:
            stylesheet: Original stylesheet
            
        Returns:
            Modified stylesheet with variables applied
        """
        # Get the accent color
        color = self._accent_color
        color_hex = color.name()
        
        # Get darker version for hover states
        darker = color.darker(120)
        darker_hex = darker.name()
        
        # Get lighter version for highlights
        lighter = color.lighter(120)
        lighter_hex = lighter.name()
        
        # Calculate transparent versions (for rgba values)
        r, g, b = color.red(), color.green(), color.blue()
        transparency_02 = f"rgba({r}, {g}, {b}, 0.2)"
        transparency_03 = f"rgba({r}, {g}, {b}, 0.3)"
        transparency_05 = f"rgba({r}, {g}, {b}, 0.5)"
        
        # Create replacements dict for accent colors (used in both themes)
        replacements = {
            # Accent color and variants
            "#ff8400": color_hex,
            "#e07800": darker_hex,
            "#d46e00": darker_hex,
            "#ff9d33": lighter_hex,
            "#ffa640": lighter_hex,
            
            # Transparencies
            "rgba(255, 132, 0, 0.2)": transparency_02,
            "rgba(255, 132, 0, 0.3)": transparency_03,
            "rgba(255, 132, 0, 0.5)": transparency_05,
        }
        
        # Apply theme-specific replacements
        if self._current_theme == "light":
            # Light theme replacements
            light_replacements = {
                # Base colors
                "#1e1e1e": "#f5f5f5",  # Background primary
                "#2a2a2a": "#e5e5e5",  # Background secondary
                "#f5f5f5": "#333333",  # Text primary
                "#aaaaaa": "#666666",  # Text secondary
                
                # Make sure selection is visible in light mode
                "background: rgba(255, 255, 255, 0.05)": "background: rgba(0, 0, 0, 0.05)",
                
                # Ensure better contrast for borders
                "border: 1px solid #2a2a2a": "border: 1px solid #cccccc",
                "border-left: 3px solid": "border-left: 3px solid",  # Preserve accent border
            }
            
            # Add these to the main replacements dict
            replacements.update(light_replacements)
        
        # Apply all replacements
        result = stylesheet
        for old, new in replacements.items():
            result = result.replace(old, new)
            
        return result
    
    def _apply_palette(self, app: QApplication) -> None:
        """
        Apply color palette to application.
        
        Args:
            app: QApplication instance
        """
        palette = QPalette()
        accent_color = self._accent_color
        
        if self._current_theme == "dark":
            # Dark theme palette
            palette.setColor(QPalette.Window, QColor("#1e1e1e"))
            palette.setColor(QPalette.WindowText, QColor("#f5f5f5"))
            palette.setColor(QPalette.Base, QColor("#2a2a2a"))
            palette.setColor(QPalette.AlternateBase, QColor("#1a1a1a"))
            palette.setColor(QPalette.ToolTipBase, QColor("#2a2a2a"))
            palette.setColor(QPalette.ToolTipText, QColor("#f5f5f5"))
            palette.setColor(QPalette.Text, QColor("#f5f5f5"))
            palette.setColor(QPalette.Button, QColor("#2a2a2a"))
            palette.setColor(QPalette.ButtonText, QColor("#f5f5f5"))
            palette.setColor(QPalette.BrightText, QColor("#ffffff"))
            palette.setColor(QPalette.Highlight, accent_color)
            palette.setColor(QPalette.HighlightedText, QColor("#000000"))
            palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#777777"))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#777777"))
        else:
            # Light theme palette
            palette.setColor(QPalette.Window, QColor("#f5f5f5"))
            palette.setColor(QPalette.WindowText, QColor("#202020"))
            palette.setColor(QPalette.Base, QColor("#ffffff"))
            palette.setColor(QPalette.AlternateBase, QColor("#e5e5e5"))
            palette.setColor(QPalette.ToolTipBase, QColor("#ffffdc"))
            palette.setColor(QPalette.ToolTipText, QColor("#000000"))
            palette.setColor(QPalette.Text, QColor("#202020"))
            palette.setColor(QPalette.Button, QColor("#e5e5e5"))
            palette.setColor(QPalette.ButtonText, QColor("#202020"))
            palette.setColor(QPalette.BrightText, QColor("#000000"))
            palette.setColor(QPalette.Highlight, accent_color)
            palette.setColor(QPalette.HighlightedText, QColor("#ffffff"))
            palette.setColor(QPalette.Disabled, QPalette.Text, QColor("#a0a0a0"))
            palette.setColor(QPalette.Disabled, QPalette.ButtonText, QColor("#a0a0a0"))
        
        app.setPalette(palette)