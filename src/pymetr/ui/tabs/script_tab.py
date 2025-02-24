# views/tabs/script_tab.py
from pathlib import Path
from typing import Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QHBoxLayout, QWidget,
    QFontComboBox, QComboBox, QLabel,
    QMessageBox
)
from PySide6.QtGui import QFont, QAction
from PySide6.QtCore import Qt, Slot

from pymetr.ui.tabs.base import BaseTab
from pymetr.ui.views.script_view import ScriptView
from pymetr.core.logging import logger

class ScriptTab(BaseTab):
    """Script editor with toolbar controls."""
    
    def __init__(self, state, model_id: str, parent=None):
        self.script_view: Optional[ScriptView] = None
        self.font_combo: Optional[QFontComboBox] = None
        self.size_combo: Optional[QComboBox] = None
        super().__init__(state, model_id, parent)

    def _setup_ui(self):
        """Initialize UI components."""
        # Set up content layout
        layout = QVBoxLayout(self.content_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Create script view
        self.script_view = ScriptView(self.state, self._model_id, self)
        layout.addWidget(self.script_view)
        
        # Set up toolbar items
        self._setup_file_actions()
        self._setup_run_controls()
        self._setup_font_controls()
        
        # Connect script view signals
        self.script_view.content_changed.connect(self._update_status)

    def _setup_file_actions(self):
        """Set up file-related actions."""
        file_menu = self.toolbar.addDropdown("File")
        
        save_action = QAction("Save", file_menu)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._handle_save)
        file_menu.addAction(save_action)
        
        self.add_toolbar_separator()

    def _setup_run_controls(self):
        """Set up run controls."""
        self.run_action = self.toolbar.addButton(
            "Run",
            callback=self._handle_run
        )
        self.run_action.setShortcut("F5")
        
        self.add_toolbar_separator()

    def _setup_font_controls(self):
        """Set up font controls."""
        # Add font controls to toolbar
        font_label = QLabel("Font:")
        # font_label.setStyleSheet("color: #D4D4D4;")
        self.add_toolbar_widget(font_label)
        
        self.font_combo = QFontComboBox()
        self.font_combo.setCurrentFont(QFont("Consolas"))
        self.font_combo.currentFontChanged.connect(self._change_font)
        self.add_toolbar_widget(self.font_combo)
        
        self.size_combo = QComboBox()
        self.size_combo.addItems([str(s) for s in [8,9,10,11,12,14,16,18,20]])
        self.size_combo.setCurrentText("11")
        self.size_combo.currentTextChanged.connect(self._change_font_size)
        self.add_toolbar_widget(self.size_combo)
        
        self.add_toolbar_stretch()

    def _change_font(self, font: QFont):
        """Update editor font family."""
        if self.script_view:
            current_font = self.script_view.editor.font()
            current_font.setFamily(font.family())
            self.script_view.set_font(current_font)

    def _change_font_size(self, size_str: str):
        """Update editor font size."""
        if not self.script_view:
            return
        try:
            size = int(size_str)
            current_font = self.script_view.editor.font()
            current_font.setPointSize(size)
            self.script_view.set_font(current_font)
        except ValueError:
            pass

    def _handle_save(self):
        """Handle save action."""
        if not self.script_view or not self.model:
            return
            
        try:
            path = self.model.get_property('script_path')
            if not path:
                self.state.set_error("No script path specified")
                return False
                
            content = self.script_view.get_content()
            Path(path).write_text(content, encoding='utf-8')
            self.script_view.set_original_content(content)
            self.state.set_info("Script saved successfully")
            return True
        except Exception as e:
            error_msg = f"Error saving script: {str(e)}"
            logger.error(error_msg)
            self.state.set_error(error_msg)
            return False

    def _handle_run(self):
        """Handle run action."""
        if not self.script_view:
            return
            
        if self.script_view.has_unsaved_changes():
            response = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save changes before running?",
                QMessageBox.Save | QMessageBox.Discard | QMessageBox.Cancel
            )
            
            if response == QMessageBox.Save:
                if not self._handle_save():
                    return
            elif response == QMessageBox.Cancel:
                return
        
        if self.model:
            self.state.set_info("Starting script execution...")
            self.state.engine.run_test_script(self.model.id)

    def _update_status(self):
        """Update status based on editor state."""
        if not self.script_view:
            return
            
        if self.script_view.has_unsaved_changes():
            self.state.set_status("Modified")
        else:
            self.state.set_status("Ready")

    def _handle_property_update(self, prop: str, value: Any):
        """Handle model property updates."""
        if not self.script_view:
            return
            
        if prop == 'status':
            status_msg = f"Status: {value}"
            
            # Different status types get different treatment
            if value == "Running":
                self.state.set_status(status_msg)
                self.script_view.set_read_only(True)
                self.run_action.setEnabled(False)
            elif value == "Failed":
                self.state.set_error(status_msg)
                self.script_view.set_read_only(False)
                self.run_action.setEnabled(True)
            elif value == "Completed":
                self.state.set_info(status_msg)
                self.script_view.set_read_only(False)
                self.run_action.setEnabled(True)
            else:
                self.state.set_status(status_msg)
                self.script_view.set_read_only(False)
                self.run_action.setEnabled(True)
                
        elif prop == 'progress':
            if value is not None:
                self.state.set_progress(value, "Script execution")

    def set_model(self, model_id: str):
        """Set up model and load content."""
        super().set_model(model_id)
        if self.model and self.script_view:
            try:
                path = self.model.get_property('script_path')
                if path and Path(path).exists():
                    content = Path(path).read_text(encoding='utf-8')
                    self.script_view.set_content(content)
                    self.script_view.set_original_content(content)
                    self.state.set_info("Script loaded successfully")
                else:
                    self.state.set_warning("Script file not found")
            except Exception as e:
                error_msg = f"Error loading script: {str(e)}"
                logger.error(error_msg)
                self.state.set_error(error_msg)