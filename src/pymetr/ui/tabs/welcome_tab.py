from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGridLayout, QSpacerItem, QSizePolicy, QFrame, QGroupBox
)
from PySide6.QtCore import Qt, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap, QFont, QColor, QPalette

from pathlib import Path
from functools import partial

from pymetr.ui.views.base import BaseWidget
from pymetr.core.actions import FileActions, InstrumentActions
from pymetr.services.file_service import FileService
from pymetr.ui.factories.parameter_factory import ParameterFactory
from pymetr.core.logging import logger


class RecentItemWidget(QFrame):
    """Widget displaying a recent file or project with click action."""
    
    clicked = Signal(str)  # Emits the item_id when clicked
    
    def __init__(self, item_id, name, item_type, timestamp=None, parent=None):
        super().__init__(parent)
        self.item_id = item_id
        
        self.setFrameShape(QFrame.StyledPanel)
        self.setFrameShadow(QFrame.Raised)
        self.setStyleSheet("""
            RecentItemWidget {
                background-color: rgba(40, 40, 40, 180);
                border-radius: 4px;
                padding: 4px;
            }
            RecentItemWidget:hover {
                background-color: rgba(60, 60, 60, 200);
            }
        """)
        
        layout = QHBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Icon based on type
        icon_label = QLabel()
        # Get icon from ParameterFactory
        icon = ParameterFactory.get_icon(item_type)
        if not icon.isNull():
            pixmap = icon.pixmap(24, 24)
            icon_label.setPixmap(pixmap)
        else:
            # Fallback
            icon_path = str(Path(__file__).parent.parent / "icons" / "file.png")
            if Path(icon_path).exists():
                pixmap = QPixmap(icon_path).scaled(24, 24, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                icon_label.setPixmap(pixmap)
            
        icon_label.setFixedSize(QSize(24, 24))
        layout.addWidget(icon_label)
        
        # Item name and info
        info_layout = QVBoxLayout()
        info_layout.setSpacing(2)
        
        name_label = QLabel(name)
        name_label.setStyleSheet("font-weight: bold; color: #DDDDDD; font-size: 13px;")
        info_layout.addWidget(name_label)
        
        if timestamp:
            time_label = QLabel(f"Last accessed: {timestamp}")
            time_label.setStyleSheet("color: #999999; font-size: 11px;")
            info_layout.addWidget(time_label)
            
        layout.addLayout(info_layout)
        layout.addStretch()
        
        # Set up click handling
        self.setMouseTracking(True)
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.item_id)
        super().mousePressEvent(event)


class LinkLabel(QLabel):
    """Clickable hyperlink-style label."""
    
    clicked = Signal(str)  # Emits the command when clicked
    
    def __init__(self, text, command, parent=None):
        super().__init__(text, parent)
        self.command = command
        self.setStyleSheet("""
            QLabel {
                color: #6ac8ff;
                text-decoration: none;
            }
            QLabel:hover {
                color: #8cd5ff;
                text-decoration: underline;
            }
        """)
        self.setCursor(Qt.PointingHandCursor)
        
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.clicked.emit(self.command)
        super().mousePressEvent(event)


class WelcomeTab(BaseWidget):
    """
    Enhanced welcome screen with quick-action buttons, recent items,
    and helpful links.
    """
    
    def __init__(self, state, parent=None):
        super().__init__(state, parent)
        
        # Get the file service instance
        self.file_service = FileService.get_instance()
        self.file_service.recent_files_changed.connect(self._refresh_recent_files)
        
        # Set up UI
        self._setup_ui()
        
        # Listen for model changes that might affect recent files
        self.state.model_registered.connect(self._on_model_registered)
        
    def _setup_ui(self):
        """Set up the enhanced welcome screen UI."""
        main_layout = QVBoxLayout(self)
        main_layout.setSpacing(20)
        main_layout.setContentsMargins(30, 30, 30, 30)
        
        # Header section
        header_layout = QHBoxLayout()
        
        # Logo/app name
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        
        app_name = QLabel("PyMetr")
        app_name.setStyleSheet("font-size: 28px; font-weight: bold; color: #FFFFFF;")
        logo_layout.addWidget(app_name)
        
        app_desc = QLabel("Test Automation Platform")
        app_desc.setStyleSheet("font-size: 14px; color: #CCCCCC;")
        logo_layout.addWidget(app_desc)
        
        header_layout.addLayout(logo_layout)
        header_layout.addStretch()
        
        # Version info
        version_label = QLabel("v0.1.0")
        version_label.setStyleSheet("font-size: 12px; color: #999999;")
        version_label.setAlignment(Qt.AlignRight | Qt.AlignTop)
        header_layout.addWidget(version_label)
        
        main_layout.addLayout(header_layout)
        
        # Main content in a grid
        content_layout = QGridLayout()
        content_layout.setSpacing(15)
        
        # === Left column: Quick actions ===
        actions_group = QGroupBox("Getting Started")
        actions_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(10)
        actions_layout.setContentsMargins(10, 20, 10, 10)  # Extra top margin for title
        
        # Create buttons layout
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)

        # Add action buttons
        icons_path = Path(__file__).parent.parent / "icons"

        # New Script Button
        new_script_btn = QPushButton("New Test Script")
        new_script_btn.setIcon(ParameterFactory.get_icon("script"))
        new_script_btn.setIconSize(QSize(32, 32))
        new_script_btn.clicked.connect(self._on_new_script)
        new_script_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px;
                font-weight: bold;
                color: white;
                background-color: #333333;
                border-radius: 4px;
                border: none;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        buttons_layout.addWidget(new_script_btn)
        
        
        # Open Script Button
        open_script_btn = QPushButton("Open Script")
        open_script_btn.setIcon(ParameterFactory.get_icon("script"))
        open_script_btn.setIconSize(QSize(32, 32))
        open_script_btn.clicked.connect(self._on_open_script)
        open_script_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px;
                font-weight: bold;
                color: white;
                background-color: #333333;
                border-radius: 4px;
                border: none;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        buttons_layout.addWidget(open_script_btn)
        
        
        # New Suite Button
        new_suite_btn = QPushButton("New Test Suite")
        new_suite_btn.setIcon(ParameterFactory.get_icon("TestSuite"))
        new_suite_btn.setIconSize(QSize(32, 32))
        new_suite_btn.clicked.connect(self._on_new_suite)
        new_suite_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px;
                font-weight: bold;
                color: white;
                background-color: #333333;
                border-radius: 4px;
                border: none;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        buttons_layout.addWidget(new_suite_btn)
        
        
        # Discover Instruments Button
        discover_btn = QPushButton("Discover Instruments")
        discover_btn.setIcon(ParameterFactory.get_icon("Device"))
        discover_btn.setIconSize(QSize(32, 32))
        discover_btn.clicked.connect(self._on_discover_instruments)
        discover_btn.setStyleSheet("""
            QPushButton {
                text-align: left;
                padding: 12px;
                font-weight: bold;
                color: white;
                background-color: #333333;
                border-radius: 4px;
                border: none;
                min-height: 50px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
            QPushButton:pressed {
                background-color: #222222;
            }
        """)
        buttons_layout.addWidget(discover_btn)
        

        # Add to layout
        actions_layout.addLayout(buttons_layout)
        actions_layout.addStretch()
        
        # Add actions GroupBox to the left column
        content_layout.addWidget(actions_group, 0, 0)
        
        # === Right column: Recent files and tips ===
        right_layout = QVBoxLayout()
        right_layout.setSpacing(15)
        
        # Recent files section in a GroupBox
        recent_group = QGroupBox("Recent Files")
        recent_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        recent_layout = QVBoxLayout(recent_group)
        recent_layout.setContentsMargins(10, 20, 10, 10)  # Extra top margin for title
        
        # Recent files container widget and layout
        self.recent_files_container = QWidget()
        self.recent_files_layout = QVBoxLayout(self.recent_files_container)
        self.recent_files_layout.setSpacing(5)
        self.recent_files_layout.setContentsMargins(0, 0, 0, 0)
        
        # Populate recent files
        self._refresh_recent_files()
        
        # Clear history link
        clear_link = LinkLabel("Clear history", "clear_history", self)
        clear_link.clicked.connect(self._on_link_clicked)
        clear_link.setAlignment(Qt.AlignRight)
        self.recent_files_layout.addWidget(clear_link)
        
        # Add the container to the recent files layout
        recent_layout.addWidget(self.recent_files_container)
        
        # Add recent files GroupBox to right layout
        right_layout.addWidget(recent_group)
        
        # Tips section in a GroupBox
        tips_group = QGroupBox("Tips & Resources")
        tips_group.setStyleSheet("""
            QGroupBox {
                font-size: 16px;
                font-weight: bold;
                color: #FFFFFF;
                border: 1px solid #444444;
                border-radius: 6px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        tips_main_layout = QVBoxLayout(tips_group)
        tips_main_layout.setContentsMargins(10, 20, 10, 10)  # Extra top margin for title
        
        tips_layout = QVBoxLayout()
        tips_layout.setSpacing(8)
        
        tips = [
            ("tutorials", "View Tutorials", "Learn how to use PyMetr effectively"),
            ("docs", "Documentation", "Access the full PyMetr documentation"),
            ("settings", "Configure Settings", "Customize PyMetr to suit your workflow"),
            ("help", "Get Help", "Ask questions and get support")
        ]
        
        for cmd, text, desc in tips:
            tip_layout = QHBoxLayout()
            
            link = LinkLabel(text, cmd, self)
            link.clicked.connect(self._on_link_clicked)
            tip_layout.addWidget(link)
            
            tip_layout.addSpacing(5)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            tip_layout.addWidget(desc_label)
            
            tip_layout.addStretch()
            tips_layout.addLayout(tip_layout)
            
        tips_main_layout.addLayout(tips_layout)
        
        # Add tips GroupBox to right layout
        right_layout.addWidget(tips_group)
        
        # Add stretch to push everything to the top
        right_layout.addStretch()
        
        # Add right layout to the right column
        content_layout.addLayout(right_layout, 0, 1)
        
        # Add the content layout to the main layout
        main_layout.addLayout(content_layout)
        
        # Footer with version and system info
        footer_layout = QHBoxLayout()
        
        # System info
        sys_info = QLabel("Powered by Python 3.10 • Qt 6.5")
        sys_info.setStyleSheet("color: #777777; font-size: 11px;")
        footer_layout.addWidget(sys_info)
        
        footer_layout.addStretch()
        
        # Check for updates link
        updates_link = LinkLabel("Check for updates", "check_updates", self)
        updates_link.clicked.connect(self._on_link_clicked)
        footer_layout.addWidget(updates_link)
        
        main_layout.addLayout(footer_layout)
        
    def _refresh_recent_files(self):
        """Refresh the recent files list."""
        # Clear existing widgets except the last one (Clear history link)
        for i in reversed(range(self.recent_files_layout.count() - 1)):
            widget = self.recent_files_layout.itemAt(i).widget()
            if widget:
                widget.setParent(None)
                widget.deleteLater()
        
        # Get recent files
        recent_files = self.file_service.get_recent_files(max_count=5)
        
        # Add placeholder if no recent files
        if not recent_files:
            no_files_label = QLabel("No recent files")
            no_files_label.setStyleSheet("color: #999999; font-style: italic;")
            no_files_label.setAlignment(Qt.AlignCenter)
            self.recent_files_layout.insertWidget(0, no_files_label)
            return
        
        # Add recent files widgets
        for idx, file_info in enumerate(recent_files):
            item_widget = RecentItemWidget(
                file_info["path"],  # Use path as ID
                file_info["name"],
                file_info["type"],
                self.file_service.format_timestamp(file_info["timestamp"]),
                self
            )
            item_widget.clicked.connect(self._on_recent_item_clicked)
            self.recent_files_layout.insertWidget(idx, item_widget)
    
    def _on_model_registered(self, model_id):
        """Handle model registration to update recent files."""
        model = self.state.get_model(model_id)
        if model and hasattr(model, 'script_path'):
            # Add script model to recent files
            self.file_service.add_recent_file(
                str(model.script_path),
                "script",
                {"model_id": model_id}
            )
    
    # === Event handlers ===
    def _on_new_script(self):
        """Handle new script button click."""
        try:
            logger.debug("WelcomeTab: Creating new script")
            FileActions.new_script(self.state)
        except Exception as e:
            logger.error(f"WelcomeTab: Error creating new script: {e}")
    
    def _on_open_script(self):
        """Handle open script button click."""
        try:
            logger.debug("WelcomeTab: Opening script")
            FileActions.open_script(self.state)
        except Exception as e:
            logger.error(f"WelcomeTab: Error opening script: {e}")
    
    def _on_new_suite(self):
        """Handle new suite button click."""
        try:
            logger.debug("WelcomeTab: Creating new suite")
            FileActions.new_suite(self.state)
        except Exception as e:
            logger.error(f"WelcomeTab: Error creating new suite: {e}")
    
    def _on_discover_instruments(self):
        """Handle discover instruments button click."""
        try:
            logger.debug("WelcomeTab: Starting instrument discovery")
            InstrumentActions.discover_instruments(self.state)
        except Exception as e:
            logger.error(f"WelcomeTab: Error discovering instruments: {e}")
    
    def _on_recent_item_clicked(self, file_path):
        """Handle recent item click."""
        logger.debug(f"WelcomeTab: Recent item clicked: {file_path}")
        
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"WelcomeTab: File no longer exists: {file_path}")
                # Remove from recent files
                self.file_service.remove_recent_file(file_path)
                return
            
            # Get metadata to see if we have a model_id
            file_entry = self.file_service.get_recent_file_entry(file_path)
            if file_entry and "metadata" in file_entry and "model_id" in file_entry["metadata"]:
                model_id = file_entry["metadata"]["model_id"]
                model = self.state.get_model(model_id)
                if model:
                    # Activate existing model
                    self.state.set_active_model(model_id)
                    return
            
            # Otherwise open based on file type
            if path.suffix.lower() == '.py':
                # Open script
                FileActions.open_script(self.state)
            elif path.suffix.lower() == '.yaml' or path.suffix.lower() == '.yml':
                # Open suite
                FileActions.open_suite(self.state)
                
        except Exception as e:
            logger.error(f"WelcomeTab: Error opening recent file: {e}")
    
    def _on_link_clicked(self, command):
        """Handle link click."""
        logger.debug(f"WelcomeTab: Link clicked with command: {command}")
        
        if command == "clear_history":
            # Clear recent files history
            self.file_service.clear_recent_files()
            logger.info("WelcomeTab: Cleared recent history")
            
        elif command == "tutorials":
            # Open tutorials
            logger.info("WelcomeTab: Opening tutorials")
            
        elif command == "docs":
            # Open documentation
            logger.info("WelcomeTab: Opening documentation")
            
        elif command == "settings":
            # Open settings
            logger.info("WelcomeTab: Opening settings")
            
        elif command == "help":
            # Open help
            logger.info("WelcomeTab: Opening help")
            
        elif command == "check_updates":
            # Check for updates
            logger.info("WelcomeTab: Checking for updates")