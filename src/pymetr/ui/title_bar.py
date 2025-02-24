import logging
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QSpacerItem, 
    QSizePolicy, QMenu
)
from PySide6.QtCore import Signal, Qt, QPoint, QSize
from PySide6.QtGui import QIcon

from pymetr.core.actions import STANDARD_ACTIONS

logger = logging.getLogger(__name__)

class TitleBar(QWidget):
    """
    A custom, frameless title bar with:
      - Menu buttons (File, Edit, Instrument, Report, Window, Options)
      - Minimize, Maximize, Close buttons
      - Window dragging support
    """
    
    windowMinimizeRequested = Signal()
    windowMaximizeRequested = Signal()
    windowCloseRequested = Signal()

    def __init__(self, parent=None, state=None):
        super().__init__(parent)
        
        self.state = state
        self._pressing = False
        self._start_pos = None
        
        self.setObjectName("TitleBar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)

        # Build absolute path to icons
        base_dir = os.path.dirname(os.path.abspath(__file__))
        self.icons_dir = os.path.join(base_dir, "icons")

        self._setup_menu_buttons()
        self._setup_window_controls()

    def _setup_menu_buttons(self):
        """Set up the menu buttons on the left side."""
        # File menu
        self.file_button = QToolButton(self)
        self.file_button.setText("File")
        self.file_button.clicked.connect(self._show_file_menu)
        self.layout.addWidget(self.file_button)

        # Edit menu
        self.edit_button = QToolButton(self)
        self.edit_button.setText("Edit")
        self.edit_button.clicked.connect(self._show_edit_menu)
        self.layout.addWidget(self.edit_button)

        # Instrument menu
        self.instrument_button = QToolButton(self)
        self.instrument_button.setText("Instrument")
        self.instrument_button.clicked.connect(self._show_instrument_menu)
        self.layout.addWidget(self.instrument_button)

        # Report menu
        self.report_button = QToolButton(self)
        self.report_button.setText("Report")
        self.report_button.clicked.connect(self._show_report_menu)
        self.layout.addWidget(self.report_button)

        # Window menu
        self.window_button = QToolButton(self)
        self.window_button.setText("Window")
        self.window_button.clicked.connect(self._show_window_menu)
        self.layout.addWidget(self.window_button)

        # Options menu
        self.options_button = QToolButton(self)
        self.options_button.setText("Options")
        self.options_button.clicked.connect(self._show_options_menu)
        self.layout.addWidget(self.options_button)

        # Add expanding spacer to push window controls right
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout.addSpacerItem(spacer)

    def _setup_window_controls(self):
        """Set up the window control buttons on the right side."""
        # Minimize button
        minimize_icon = os.path.join(self.icons_dir, "minimize.png")
        self.minimize_button = QToolButton()
        self.minimize_button.setIcon(QIcon(minimize_icon))
        self.minimize_button.setIconSize(QSize(24, 24))
        self.minimize_button.clicked.connect(self.on_minimize_clicked)
        self.layout.addWidget(self.minimize_button)

        # Maximize button
        maximize_icon = os.path.join(self.icons_dir, "maximize.png")
        self.maximize_button = QToolButton()
        self.maximize_button.setIcon(QIcon(maximize_icon))
        self.maximize_button.setIconSize(QSize(24, 24))
        self.maximize_button.clicked.connect(self.on_maximize_clicked)
        self.layout.addWidget(self.maximize_button)

        # Close button
        close_icon = os.path.join(self.icons_dir, "close.png")
        self.close_button = QToolButton()
        self.close_button.setIcon(QIcon(close_icon))
        self.close_button.setIconSize(QSize(24, 24))
        self.close_button.clicked.connect(self.on_close_clicked)
        self.layout.addWidget(self.close_button)

    def _show_file_menu(self):
        menu = QMenu(self)
        
        # New submenu
        new_menu = menu.addMenu("New")
        new_menu.addAction("Suite", lambda: self._trigger_action('new_suite'))
        new_menu.addAction("Script", lambda: self._trigger_action('new_script'))
        
        # Open submenu
        open_menu = menu.addMenu("Open")
        open_menu.addAction("Suite", lambda: self._trigger_action('open_suite'))
        open_menu.addAction("Script", lambda: self._trigger_action('open_script'))
        
        menu.addSeparator()
        
        # Save actions
        menu.addAction("Save", lambda: self._trigger_action('save_script'))
        menu.addAction("Save Suite", lambda: self._trigger_action('save_suite'))
        
        menu.addSeparator()
        
        # Data submenu
        data_menu = menu.addMenu("Data")
        data_menu.addAction("Load Data")
        data_menu.addAction("Save Data")
        
        # State submenu
        state_menu = menu.addMenu("State")
        state_menu.addAction("Load State")
        state_menu.addAction("Save State")
        
        menu.exec_(self.file_button.mapToGlobal(QPoint(0, self.file_button.height())))

    def _show_edit_menu(self):
        menu = QMenu(self)
        menu.addAction("Create Result")
        menu.addAction("Create Plot")
        
        markers_menu = menu.addMenu("Markers")
        markers_menu.addAction("Create Marker")
        markers_menu.addAction("Create Cursor")
        
        menu.exec_(self.edit_button.mapToGlobal(QPoint(0, self.edit_button.height())))

    def _show_instrument_menu(self):
        menu = QMenu(self)
        menu.addAction("Discover", lambda: self._trigger_action('discover_instruments'))
        menu.addAction("Load Driver")
        menu.addAction("Mock Instrument")
        
        menu.exec_(self.instrument_button.mapToGlobal(QPoint(0, self.instrument_button.height())))

    def _show_report_menu(self):
        menu = QMenu(self)
        menu.addAction("Generate")
        menu.addAction("Load Template")
        menu.addAction("New Template")
        menu.addSeparator()
        menu.addAction("Preferences")
        
        menu.exec_(self.report_button.mapToGlobal(QPoint(0, self.report_button.height())))

    def _show_window_menu(self):
        menu = QMenu(self)
        menu.addAction("Default Layout")
        menu.addSeparator()
        menu.addAction("Show/Hide Instrument Dock")
        menu.addAction("Show/Hide Console")
        
        menu.exec_(self.window_button.mapToGlobal(QPoint(0, self.window_button.height())))

    def _show_options_menu(self):
        menu = QMenu(self)
        menu.addAction("Settings")
        
        menu.exec_(self.options_button.mapToGlobal(QPoint(0, self.options_button.height())))

    def _trigger_action(self, action_id: str):
        """Trigger a standard action if available and executable."""
        if not self.state:
            logger.warning("TitleBar has no 'state'; cannot run action.")
            return

        action_obj = STANDARD_ACTIONS.get(action_id)
        if not action_obj:
            logger.warning(f"No STANDARD_ACTIONS entry for '{action_id}'")
            return

        if not action_obj.can_execute(self.state):
            logger.warning(f"Action '{action_id}' cannot execute in current state.")
            return

        logger.debug(f"TitleBar: calling handler for '{action_id}'")
        action_obj.handler(self.state)

    # Window control handlers
    def on_minimize_clicked(self):
        self.windowMinimizeRequested.emit()

    def on_maximize_clicked(self):
        self.windowMaximizeRequested.emit()

    def on_close_clicked(self):
        self.windowCloseRequested.emit()

    # Window dragging support
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._pressing = True
            self._start_pos = event.globalPosition().toPoint()

    def mouseMoveEvent(self, event):
        if self._pressing and event.buttons() & Qt.LeftButton:
            parent = self.window()
            if parent:
                delta = event.globalPosition().toPoint() - self._start_pos
                new_pos = parent.pos() + delta
                parent.move(new_pos)
                self._start_pos = event.globalPosition().toPoint()

    def mouseReleaseEvent(self, event):
        self._pressing = False