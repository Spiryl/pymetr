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
        # self.setStyleSheet("""
        #     RecentItemWidget {
        #         background-color: #1e1e1e;
        #         border-radius: 4px;
        #         padding: 4px;
        #     }
        #     RecentItemWidget:hover {
        #         background-color: rgba(60, 60, 60, 200);
        #     }
        # """)
        
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
        
        # Add header section
        main_layout.addLayout(self._create_header_section())
        
        # Main content in a grid
        content_layout = QGridLayout()
        content_layout.setSpacing(15)
        
        # Left column (Getting Started and Recent Files)
        actions_group = self._create_getting_started_section()
        content_layout.addWidget(actions_group, 0, 0)
        
        recent_group = self._create_recent_files_section()
        content_layout.addWidget(recent_group, 1, 0)
        
        # Right column (Example Scripts and Help & Resources)
        right_container = QWidget()
        right_layout = QVBoxLayout(right_container)
        right_layout.setSpacing(15)
        right_layout.setContentsMargins(0, 0, 0, 0)
        right_layout.setAlignment(Qt.AlignTop)
        
        examples_group = self._create_examples_section()
        right_layout.addWidget(examples_group)
        
        tips_group = self._create_help_resources_section()
        right_layout.addWidget(tips_group)
        
        right_layout.addStretch(1)
        content_layout.addWidget(right_container, 0, 1, 2, 1)
        
        # Set column stretch to make the columns equal width
        content_layout.setColumnStretch(0, 1)
        content_layout.setColumnStretch(1, 1)
        
        # Add the content layout to the main layout
        main_layout.addLayout(content_layout)
        
        # Add footer section
        main_layout.addLayout(self._create_footer_section())

    def _create_header_section(self):
        """Create the header section with app name and version."""
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
        
        return header_layout

    def _create_getting_started_section(self):
        """Create the Getting Started section with action buttons."""
        actions_group = QGroupBox("Getting Started")
        actions_group.setStyleSheet(self._get_group_box_style())
        
        actions_layout = QVBoxLayout(actions_group)
        actions_layout.setSpacing(10)
        actions_layout.setContentsMargins(10, 20, 10, 10)
        
        # Create buttons
        buttons_layout = QVBoxLayout()
        buttons_layout.setSpacing(10)
        
        # Define the buttons to create
        buttons = [
            ("New Test Script", "script", self._on_new_script),
            ("Open Script", "script", self._on_open_script),
            ("New Test Suite", "TestSuite", self._on_new_suite),
            ("Discover Instruments", "Device", self._on_discover_instruments)
        ]
        
        # Create and add each button
        for text, icon_name, callback in buttons:
            btn = QPushButton(text)
            btn.setIcon(ParameterFactory.get_icon(icon_name))
            btn.setIconSize(QSize(32, 32))
            btn.clicked.connect(callback)
            btn.setStyleSheet(self._get_button_style())
            buttons_layout.addWidget(btn)
        
        actions_layout.addLayout(buttons_layout)
        actions_layout.addStretch()
        
        return actions_group

    def _create_recent_files_section(self):
        """Create the Recent Files section."""
        recent_group = QGroupBox("Recent Files")
        recent_group.setStyleSheet(self._get_group_box_style())
        
        recent_layout = QVBoxLayout(recent_group)
        recent_layout.setContentsMargins(10, 20, 10, 10)
        
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
        
        recent_layout.addWidget(self.recent_files_container)
        
        return recent_group

    def _create_examples_section(self):
        """Create the Example Scripts section with dynamic content loading."""
        examples_group = QGroupBox("Example Scripts")
        examples_group.setStyleSheet(self._get_group_box_style())
        
        examples_layout = QVBoxLayout(examples_group)
        examples_layout.setContentsMargins(10, 20, 10, 10)
        
        # Load examples dynamically from the scripts directory
        scripts_dir = Path(__file__).parent.parent.parent / "scripts"
        if scripts_dir.exists():
            # Look for example scripts in the scripts directory
            example_files = self._find_example_scripts(scripts_dir)
            
            # If no examples found in scripts dir, use hardcoded defaults
            if not example_files:
                example_files = [
                    ("Simple Plot", "A1 - Simple Plot.py", "Create a basic visualization"),
                    ("Real-Time Plot", "A2 - Real Time Plot.py", "Live data plotting"),
                    ("Test Results", "A3 - Test Results.py", "Working with test results"),
                    ("Multiple Plots", "A4 - Multiple Plots.py", "Compare multiple datasets")
                ]
        else:
            # Fallback to hardcoded examples
            example_files = [
                ("Simple Plot", "A1 - Simple Plot.py", "Create a basic visualization"),
                ("Real-Time Plot", "A2 - Real Time Plot.py", "Live data plotting"),
                ("Test Results", "A3 - Test Results.py", "Working with test results"),
                ("Multiple Plots", "A4 - Multiple Plots.py", "Compare multiple datasets")
            ]
        
        for title, filename, desc in example_files:
            example_layout = QHBoxLayout()
            
            example_link = LinkLabel(title, f"example:{filename}", self)
            example_link.clicked.connect(self._on_link_clicked)
            example_layout.addWidget(example_link)
            
            example_layout.addSpacing(5)
            
            desc_label = QLabel(desc)
            desc_label.setStyleSheet("color: #AAAAAA; font-size: 11px;")
            example_layout.addWidget(desc_label)
            
            example_layout.addStretch()
            examples_layout.addLayout(example_layout)
        
        return examples_group

    def _create_help_resources_section(self):
        """Create the Help & Resources section."""
        tips_group = QGroupBox("Help & Resources")
        tips_group.setStyleSheet(self._get_group_box_style())
        
        tips_main_layout = QVBoxLayout(tips_group)
        tips_main_layout.setContentsMargins(10, 20, 10, 10)
        
        tips_layout = QVBoxLayout()
        tips_layout.setSpacing(8)
        
        # Try to find docs in the docs directory
        docs_dir = Path(__file__).parent.parent.parent.parent / "docs"
        
        if docs_dir.exists() and self._has_markdown_files(docs_dir):
            # Use local docs if available
            tips = self._gather_documentation_links(docs_dir)
        else:
            # Fallback to defaults
            tips = [
                ("tutorials", "View Tutorials", "Learn how to use PyMetr effectively", "local"),
                ("docs", "Documentation", "Access the full PyMetr documentation", "web"),
                ("settings", "Configure Settings", "Customize PyMetr to suit your workflow", "local"),
                ("help", "Get Help", "Ask questions and get support", "local")
            ]
        
        for cmd, text, desc, link_type in tips:
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
        
        return tips_group

    def _create_footer_section(self):
        """Create the footer section with system info and update link."""
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
        
        return footer_layout

    def _get_group_box_style(self):
        """Return the common GroupBox style."""
        return """
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
        """

    def _get_button_style(self):
        """Return the common Button style."""
        return """
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
        """

    def _find_example_scripts(self, scripts_dir):
        """
        Find example scripts in the given directory.
        Returns a list of tuples: (title, filename, description)
        """
        example_files = []
        
        try:
            # Look for Python files in the scripts directory
            script_files = list(scripts_dir.glob("*.py"))
            script_files.extend(scripts_dir.glob("*/*.py"))  # Include subdirectories
            
            for script_path in script_files:
                # Skip __init__.py and other special files
                if script_path.name.startswith("__"):
                    continue
                    
                # Create a display name from the filename
                title = script_path.stem.replace("_", " ").title()
                
                # Extract description from file docstring if available
                desc = self._extract_script_description(script_path)
                if not desc:
                    desc = f"Example script: {title}"
                    
                # Make path relative to scripts_dir for storage
                rel_path = script_path.relative_to(scripts_dir)
                example_files.append((title, str(rel_path), desc))
            
            # Sort by filename for a consistent order
            example_files.sort(key=lambda x: x[1])
            
        except Exception as e:
            logger.error(f"Error finding example scripts: {e}")
        
        return example_files

    def _extract_script_description(self, script_path):
        """Extract the description from a script's docstring."""
        try:
            with open(script_path, 'r') as f:
                content = f.read()
                
            # Look for docstring
            import ast
            try:
                module = ast.parse(content)
                docstring = ast.get_docstring(module)
                if docstring:
                    # Get the first line or first sentence
                    return docstring.split('\n')[0].strip()
            except:
                pass
                
            # Fallback: Look for comments near the top
            lines = content.split('\n')
            for line in lines[:10]:  # Check first 10 lines
                if line.strip().startswith('#') and len(line) > 2:
                    return line.strip('# ').strip()
        except Exception as e:
            logger.debug(f"Error extracting script description: {e}")
        
        return None

    def _has_markdown_files(self, docs_dir):
        """Check if the docs directory has markdown files."""
        try:
            md_files = list(docs_dir.glob("*.md"))
            rst_files = list(docs_dir.glob("*.rst"))
            return len(md_files) > 0 or len(rst_files) > 0
        except Exception:
            return False

    def _gather_documentation_links(self, docs_dir):
        """
        Gather documentation links from markdown/rst files.
        Returns a list of tuples: (command, title, description, link_type)
        """
        doc_links = []
        
        try:
            # Find markdown and RST files
            md_files = list(docs_dir.glob("*.md"))
            rst_files = list(docs_dir.glob("*.rst"))
            doc_files = md_files + rst_files
            
            for doc_path in doc_files:
                # Skip certain files like README or LICENSE
                if doc_path.name.lower() in ("readme.md", "license.md", "contributing.md"):
                    continue
                    
                # Create a display name from the filename
                title = doc_path.stem.replace("_", " ").replace("-", " ").title()
                
                # Extract description from file content if available
                desc = self._extract_doc_description(doc_path)
                if not desc:
                    desc = f"Documentation: {title}"
                    
                # Command uses the file path
                cmd = f"doc:{doc_path}"
                doc_links.append((cmd, title, desc, "local"))
            
            # Add link to external RTD if available
            doc_links.append(("web:docs", "Read the Docs", "View online documentation", "web"))
            
            # Sort alphabetically by title
            doc_links.sort(key=lambda x: x[1])
            
        except Exception as e:
            logger.error(f"Error gathering documentation links: {e}")
            # Fallback to defaults
            doc_links = [
                ("tutorials", "View Tutorials", "Learn how to use PyMetr effectively", "local"),
                ("docs", "Documentation", "Access the full PyMetr documentation", "web"),
                ("settings", "Configure Settings", "Customize PyMetr to suit your workflow", "local"),
                ("help", "Get Help", "Ask questions and get support", "local")
            ]
        
        return doc_links

    def _extract_doc_description(self, doc_path):
        """Extract a description from markdown/rst documentation."""
        try:
            with open(doc_path, 'r') as f:
                content = f.read(1000)  # Just read the beginning
                
            lines = content.split('\n')
            
            # Skip title line if it exists
            start_idx = 0
            if lines and (lines[0].startswith('#') or lines[0].startswith('=')):
                start_idx = 1
                
            # Look for first non-empty line that's not a heading
            for line in lines[start_idx:]:
                line = line.strip()
                if line and not line.startswith('#') and not line.startswith('='):
                    # Truncate if too long
                    if len(line) > 60:
                        return line[:57] + "..."
                    return line
        except Exception as e:
            logger.debug(f"Error extracting doc description: {e}")
        
        return None

        
    def _on_link_clicked(self, command):
        """Handle link click."""
        logger.debug(f"WelcomeTab: Link clicked with command: {command}")
        
        if command == "clear_history":
            # Clear recent files history
            self.file_service.clear_recent_files()
            logger.info("WelcomeTab: Cleared recent history")
            
        elif command.startswith("example:"):
            # Open example script
            script_name = command.split(":", 1)[1]
            try:
                # Find the example script in the scripts directory
                scripts_dir = Path(__file__).parent.parent.parent / "scripts"
                example_path = scripts_dir / script_name
                
                if not example_path.exists():
                    logger.warning(f"WelcomeTab: Example file does not exist: {example_path}")
                    return
                    
                # Add to recent files first
                self.file_service.add_recent_file(str(example_path), "script")
                
                # Create a new TestScript model and add it to the state
                from pymetr.models.test import TestScript
                script = self.state.create_model(TestScript, script_path=example_path)
                
                # Make it the active model
                self.state.set_active_model(script.id)
                
                logger.info(f"WelcomeTab: Opened example script: {script_name}")
                
            except Exception as e:
                logger.error(f"WelcomeTab: Error opening example script: {e}")
        
        elif command.startswith("doc:"):
            # Open local documentation
            doc_path = command.split(":", 1)[1]
            try:
                self._open_documentation(doc_path)
            except Exception as e:
                logger.error(f"WelcomeTab: Error opening documentation: {e}")
        
        elif command.startswith("web:"):
            # Open web documentation
            if command == "web:docs":
                url = "https://pymetr.readthedocs.io/"
                self._open_web_documentation(url)
                
        # Handle other link types (unchanged)
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

    def _open_documentation(self, doc_path):
        """Open local documentation file."""
        try:
            path = Path(doc_path)
            if not path.exists():
                logger.warning(f"Documentation file not found: {path}")
                return
                
            # TODO: Implement a documentation viewer tab
            logger.info(f"Opening documentation: {path.name}")
            
            # For now, we can use the default system application
            import webbrowser
            webbrowser.open(path.as_uri())
        except Exception as e:
            logger.error(f"Error opening documentation: {e}")

    def _open_web_documentation(self, url):
        """Open web documentation in browser or embedded view."""
        try:
            # TODO: Consider adding an embedded web view
            logger.info(f"Opening web documentation: {url}")
            
            # For now, open in system browser
            import webbrowser
            webbrowser.open(url)
        except Exception as e:
            logger.error(f"Error opening web documentation: {e}")
        
        # Check for updates link
        updates_link = LinkLabel("Check for updates", "check_updates", self)
        updates_link.clicked.connect(self._on_link_clicked)
        # footer_layout.addWidget(updates_link)
        
        # main_layout.addLayout(footer_layout)
        
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
    