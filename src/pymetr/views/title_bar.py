# pymetr/views/title_bar.py

import logging
import os
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QToolButton, QSpacerItem, 
    QSizePolicy, QMenu
)
from PySide6.QtCore import Signal, Qt, QPoint, QSize
from PySide6.QtGui import QIcon

# Import your standard actions
from pymetr.core.actions import STANDARD_ACTIONS

logger = logging.getLogger(__name__)

class TitleBar(QWidget):
    """
    A custom, frameless title bar with:
      - "File," "Report," "Automation," "Window" QToolButtons
      - Minimize, Maximize, Close buttons
      - Optionally hooking up actions from STANDARD_ACTIONS
    """
    
    windowMinimizeRequested = Signal()
    windowMaximizeRequested = Signal()
    windowCloseRequested = Signal()

    def __init__(self, parent=None, state=None):
        """
        Pass in 'state' so we can call e.g. STANDARD_ACTIONS['open_script'].handler(state)
        """
        super().__init__(parent)
        
        self.state = state    # Store the app state to run actions
        self._pressing = False
        self._start_pos = None
        
        self.setObjectName("TitleBar")
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 5, 5, 5)
        self.layout.setSpacing(10)

        # Build absolute path to icons
        base_dir = os.path.dirname(os.path.abspath(__file__))
        icons_dir = os.path.join(base_dir, "icons")

        # ---------- "File" QToolButton ----------
        self.file_button = QToolButton(self)
        self.file_button.setText("File")
        self.file_button.clicked.connect(self.on_file_menu_clicked)
        self.layout.addWidget(self.file_button)

        # ---------- "Report" Button ----------
        self.report_button = QToolButton(self)
        self.report_button.setText("Report")
        # If you'd like a menu or direct action, handle similarly
        # self.report_button.clicked.connect(self.on_report_menu_clicked)
        self.layout.addWidget(self.report_button)

        # ---------- "Automation" Button ----------
        self.automation_button = QToolButton(self)
        self.automation_button.setText("Automation")
        # self.automation_button.clicked.connect(self.on_automation_menu_clicked)
        self.layout.addWidget(self.automation_button)

        # ---------- "Window" Button ----------
        self.window_button = QToolButton(self)
        self.window_button.setText("Window")
        # Possibly open a QMenu or do something else
        self.layout.addWidget(self.window_button)

        # ---------- Spacer pushes window-controls to the right ----------
        spacer = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        self.layout.addSpacerItem(spacer)

        # ---------- Window control buttons ----------
        minimize_icon = os.path.join(icons_dir, "minimize.png")
        self.minimize_button = QToolButton()
        self.minimize_button.setIcon(QIcon(minimize_icon))
        self.minimize_button.setIconSize(QSize(24, 24))
        self.minimize_button.clicked.connect(self.on_minimize_clicked)
        self.layout.addWidget(self.minimize_button)

        maximize_icon = os.path.join(icons_dir, "maximize.png")
        self.maximize_button = QToolButton()
        self.maximize_button.setIcon(QIcon(maximize_icon))
        self.maximize_button.setIconSize(QSize(24, 24))
        self.maximize_button.clicked.connect(self.on_maximize_clicked)
        self.layout.addWidget(self.maximize_button)

        close_icon = os.path.join(icons_dir, "close.png")
        self.close_button = QToolButton()
        self.close_button.setIcon(QIcon(close_icon))
        self.close_button.setIconSize(QSize(24, 24))
        self.close_button.clicked.connect(self.on_close_clicked)
        self.layout.addWidget(self.close_button)

        # Style your title bar as you wish
        self.setStyleSheet("""
            QWidget#TitleBar {
                background-color: #2D2D2D;
            }
            QToolButton {
                color: #FFFFFF;
                background: transparent;
                border: none;
            }
            QToolButton:hover {
                background-color: rgba(255,255,255,0.1);
            }
        """)

    # ----------------------------------------------------------------------
    # EXAMPLE: "File" button -> QMenu -> standard actions
    # ----------------------------------------------------------------------
    def on_file_menu_clicked(self):
        """
        Create a QMenu with "New," "Open," "Save" that call standard actions
        by hooking up to e.g. STANDARD_ACTIONS['new_script'].handler(self.state)
        """
        menu = QMenu(self)

        # "New Script"
        action_new = menu.addAction("New Script")
        action_new.triggered.connect(lambda: self._trigger_action('new_script'))

        # "Open Script"
        action_open = menu.addAction("Open Script")
        action_open.triggered.connect(lambda: self._trigger_action('open_script'))

        # "Save Script"
        action_save = menu.addAction("Save Script")
        action_save.triggered.connect(lambda: self._trigger_action('save_script'))

        # Show the QMenu under the File button
        pos = self.file_button.mapToGlobal(QPoint(0, self.file_button.height()))
        menu.exec_(pos)

    def _trigger_action(self, action_id: str):
        """
        Utility: calls the relevant STANDARD_ACTIONS action handler
        if it 'can_execute' on the current state.
        """
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

    # ----------------------------------------------------------------------
    # Window control: we simply emit signals that the main window connects
    # ----------------------------------------------------------------------
    def on_minimize_clicked(self):
        self.windowMinimizeRequested.emit()

    def on_maximize_clicked(self):
        self.windowMaximizeRequested.emit()

    def on_close_clicked(self):
        self.windowCloseRequested.emit()

    # ----------------------------------------------------------------------
    # Enable window dragging by the title bar
    # ----------------------------------------------------------------------
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
