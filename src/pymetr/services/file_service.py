from pathlib import Path
from typing import Dict, Any, Optional, Tuple, List
from datetime import datetime
import yaml
import json
import os

from PySide6.QtWidgets import QWidget, QFileDialog
from PySide6.QtCore import QObject, QSettings, Signal

from pymetr.core.logging import logger
from pymetr.models.test import TestSuite, TestScript

class FileService(QObject):
    """
    Service for file operations, model import/export, and recent file history.
    Provides a centralized API for all file-related functionality.
    """
    
    # Signals
    recent_files_changed = Signal()  # Emitted when recent files list changes
    
    # Singleton instance
    _instance = None
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of FileService."""
        if cls._instance is None:
            cls._instance = FileService()
        return cls._instance
    
    def __init__(self):
        """Initialize FileService."""
        super().__init__()
        self._settings = QSettings("PyMetr", "PyMetr")
        self._recent_files = []
        self._max_recent_files = 10
        self._load_recent_files()

    # ===== Recent Files Methods =====
    
    def add_recent_file(self, file_path: str, file_type: str = "script", metadata: Optional[Dict] = None):
        """
        Add a file to the recent files list.
        
        Args:
            file_path: Path to the file
            file_type: Type of file (script, suite, etc.)
            metadata: Optional metadata about the file
        """
        try:
            path = Path(file_path)
            if not path.exists():
                logger.warning(f"FileService: File does not exist: {file_path}")
                return
                
            # Normalize the path
            file_path = str(path.resolve())
            
            # Create entry
            entry = {
                "path": file_path,
                "name": path.stem,
                "type": file_type,
                "timestamp": datetime.now().isoformat(),
                "metadata": metadata or {}
            }
            
            # Remove if already exists
            self._recent_files = [f for f in self._recent_files if f["path"] != file_path]
            
            # Add at the beginning
            self._recent_files.insert(0, entry)
            
            # Limit the number of entries
            self._recent_files = self._recent_files[:self._max_recent_files]
            
            # Save changes
            self._save_recent_files()
            
            # Emit signal
            self.recent_files_changed.emit()
            
            logger.debug(f"FileService: Added file to recent list: {path.name}")
            
        except Exception as e:
            logger.error(f"FileService: Error adding recent file: {e}")
    
    def remove_recent_file(self, file_path: str):
        """
        Remove a file from the recent files list.
        
        Args:
            file_path: Path to the file to remove
        """
        try:
            # Normalize the path
            path = Path(file_path)
            file_path = str(path.resolve())
            
            # Remove if exists
            orig_count = len(self._recent_files)
            self._recent_files = [f for f in self._recent_files if f["path"] != file_path]
            
            if len(self._recent_files) < orig_count:
                # Save changes
                self._save_recent_files()
                
                # Emit signal
                self.recent_files_changed.emit()
                
                logger.debug(f"FileService: Removed file from recent list: {path.name}")
            
        except Exception as e:
            logger.error(f"FileService: Error removing recent file: {e}")
    
    def clear_recent_files(self):
        """Clear the recent files list."""
        try:
            self._recent_files = []
            self._save_recent_files()
            self.recent_files_changed.emit()
            logger.debug("FileService: Cleared recent files list")
            
        except Exception as e:
            logger.error(f"FileService: Error clearing recent files: {e}")
    
    def get_recent_files(self, file_type: Optional[str] = None, max_count: Optional[int] = None) -> List[Dict]:
        """
        Get the list of recent files, optionally filtered by type.
        
        Args:
            file_type: Optional type filter
            max_count: Optional limit on number of results
            
        Returns:
            List of recent file entries
        """
        try:
            # Filter by type if requested
            result = self._recent_files
            if file_type:
                result = [f for f in result if f["type"] == file_type]
                
            # Limit count if requested
            if max_count:
                result = result[:max_count]
                
            return result
            
        except Exception as e:
            logger.error(f"FileService: Error getting recent files: {e}")
            return []
    
    def format_timestamp(self, timestamp_str: str) -> str:
        """
        Format a timestamp string into a user-friendly format.
        
        Args:
            timestamp_str: ISO format timestamp string
            
        Returns:
            User-friendly formatted time string
        """
        try:
            # Parse the timestamp
            dt = datetime.fromisoformat(timestamp_str)
            now = datetime.now()
            
            # Format based on how recent it is
            if dt.date() == now.date():
                return f"Today at {dt.strftime('%I:%M %p')}"
            elif (now.date() - dt.date()).days == 1:
                return f"Yesterday at {dt.strftime('%I:%M %p')}"
            elif (now.date() - dt.date()).days < 7:
                return f"{dt.strftime('%A')} at {dt.strftime('%I:%M %p')}"
            else:
                return f"{dt.strftime('%B %d, %Y')}"
                
        except Exception as e:
            logger.error(f"FileService: Error formatting timestamp: {e}")
            return timestamp_str
    
    def is_in_recent_files(self, file_path: str) -> bool:
        """
        Check if a file exists in the recent files list.
        
        Args:
            file_path: Path to check
            
        Returns:
            True if the file exists in the list
        """
        try:
            # Normalize the path
            path = Path(file_path)
            file_path = str(path.resolve())
            
            # Check if exists
            return any(f["path"] == file_path for f in self._recent_files)
            
        except Exception as e:
            logger.error(f"FileService: Error checking recent file existence: {e}")
            return False
    
    def get_recent_file_entry(self, file_path: str) -> Optional[Dict]:
        """
        Get the entry for a specific file.
        
        Args:
            file_path: Path to the file
            
        Returns:
            File entry or None if not found
        """
        try:
            # Normalize the path
            path = Path(file_path)
            file_path = str(path.resolve())
            
            # Find the entry
            for entry in self._recent_files:
                if entry["path"] == file_path:
                    return entry
                    
            return None
            
        except Exception as e:
            logger.error(f"FileService: Error getting recent file entry: {e}")
            return None
            
    def _load_recent_files(self):
        """Load recent files from QSettings."""
        try:
            # Get the JSON data from settings
            json_data = self._settings.value("recentFiles")
            if json_data:
                self._recent_files = json.loads(json_data)
                
                # Filter out files that no longer exist
                self._recent_files = [
                    f for f in self._recent_files 
                    if Path(f["path"]).exists()
                ]
                
                # Save filtered list
                self._save_recent_files()
                
            logger.debug(f"FileService: Loaded {len(self._recent_files)} recent files")
            
        except Exception as e:
            logger.error(f"FileService: Error loading recent files: {e}")
            self._recent_files = []
            
    def _save_recent_files(self):
        """Save recent files to QSettings."""
        try:
            # Convert to JSON and save
            json_data = json.dumps(self._recent_files)
            self._settings.setValue("recentFiles", json_data)
            self._settings.sync()
            
            logger.debug(f"FileService: Saved {len(self._recent_files)} recent files")
            
        except Exception as e:
            logger.error(f"FileService: Error saving recent files: {e}")

    # ===== File Operation Methods =====
    
    @staticmethod
    def export_model_data(model_id: str, state, path: Path) -> bool:
        """Export model and its children to YAML."""
        try:
            model = state.get_model(model_id)
            if not model:
                return False
                
            data = FileService._export_model(model, state)
                
            # Write to file
            with open(path, 'w') as f:
                yaml.dump(data, f)
                
            # Add to recent files
            FileService.get_instance().add_recent_file(
                str(path), 
                "suite", 
                {"model_id": model_id}
            )
                
            return True
            
        except Exception as e:
            logger.error(f"FileService: Error exporting model data: {e}")
            return False

    @staticmethod
    def _export_model(model, state) -> Dict:
        """Recursively export a model and its children."""
        data = {
            'type': type(model).__name__,
            'properties': model._properties,
            'children': []
        }
        
        # Export children recursively
        for child in state.get_children(model.id):
            child_data = FileService._export_model(child, state)
            data['children'].append(child_data)
            
        return data

    @staticmethod
    def import_model_data(path: Path, state) -> Optional[str]:
        """Import model data from YAML, returns root model ID."""
        try:
            with open(path) as f:
                data = yaml.safe_load(f)
            
            model_id = FileService._import_model(data, state)
            
            # If successful, add to recent files
            if model_id:
                FileService.get_instance().add_recent_file(
                    str(path), 
                    "suite", 
                    {"model_id": model_id}
                )
                
            return model_id
            
        except Exception as e:
            logger.error(f"FileService: Error importing model data: {e}")
            return None

    @staticmethod
    def _import_model(data: Dict, state) -> Optional[str]:
        """Recursively import a model and its children."""
        try:
            # Import model based on type
            model_type = data['type']
            properties = data.get('properties', {})
            
            # Create model instance
            if model_type == 'TestSuite':
                model = state.create_model(TestSuite)
            elif model_type == 'TestScript':
                script_path = properties.get('script_path')
                if script_path:
                    script_path = Path(script_path)
                    model = state.create_model(TestScript, script_path=script_path)
                else:
                    logger.error("TestScript missing script_path")
                    return None
            else:
                # Handle other model types...
                return None
                
            # Set properties
            for key, value in properties.items():
                model.set_property(key, value)
                
            # Import children recursively
            for child_data in data.get('children', []):
                child_id = FileService._import_model(child_data, state)
                if child_id:
                    state.link_models(model.id, child_id)
                    
            return model.id
            
        except Exception as e:
            logger.error(f"FileService: Error importing model: {e}")
            return None

    @staticmethod
    def open_suite(parent: Optional[QWidget] = None) -> Tuple[bool, Optional[Path], str]:
        """Handle suite opening UI and file operations."""
        if parent:
            file_path, _ = QFileDialog.getOpenFileName(
                parent,
                "Open Test Suite",
                str(Path.home()),
                "YAML Files (*.yaml)"
            )
            if file_path:
                try:
                    path = Path(file_path)
                    if path.exists():
                        return True, path, ""
                except Exception as e:
                    logger.error(f"FileService: Error opening suite: {e}")
                    return False, None, str(e)
                    
        return False, None, "No parent widget provided"

    @staticmethod
    def save_suite(suite: TestSuite, parent: Optional[QWidget] = None) -> Tuple[bool, Optional[Path], str]:
        """Handle suite saving UI and file operations."""
        if not parent:
            return False, None, "No parent widget provided"
            
        try:
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Save Test Suite",
                str(Path.home()),
                "YAML Files (*.yaml)"
            )
            
            if file_path:
                path = Path(file_path)
                if not path.suffix:
                    path = path.with_suffix('.yaml')
                    
                success = FileService.export_model_data(suite.id, suite.state, path)
                if success:
                    return True, path, ""
                else:
                    return False, None, "Failed to export suite data"
                    
        except Exception as e:
            logger.error(f"FileService: Error saving suite: {e}")
            return False, None, str(e)
            
        return False, None, "Operation cancelled"