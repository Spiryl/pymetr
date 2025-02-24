from pathlib import Path
from typing import Optional, Tuple
from PySide6.QtWidgets import QWidget, QFileDialog, QMessageBox

from pymetr.models.test import TestScript
from pymetr.services.file_service import FileService
from pymetr.core.logging import logger

class ScriptService:
    """Handles script-related operations."""
    
    @staticmethod
    def create_script(parent: Optional[QWidget] = None) -> Tuple[bool, Optional[Path], str]:
        """
        Handle script creation UI and file operations.
        Returns: (success, path, error_message)
        """
        if parent:
            file_path, _ = QFileDialog.getSaveFileName(
                parent,
                "Create New Script",
                str(Path.home()),
                "Python Files (*.py)"
            )
            if file_path:
                path = Path(file_path)
                if not path.suffix:
                    path = path.with_suffix('.py')
                    
                try:
                    if not path.exists():
                        path.write_text(
                            "def run_test():\n"
                            "    # Your test code here\n"
                            "    pass\n"
                        )
                    
                    # Add to recent files
                    file_service = FileService.get_instance()
                    file_service.add_recent_file(str(path), "script")
                    
                    return True, path, ""
                    
                except Exception as e:
                    logger.error(f"ScriptService: Error creating script: {e}")
                    return False, None, str(e)
                    
        return False, None, "No parent widget provided"

    @staticmethod
    def open_script(parent: Optional[QWidget] = None) -> Tuple[bool, Optional[Path], str]:
        """
        Handle script opening UI and file operations.
        Returns: (success, path, error_message)
        """
        if parent:
            file_path, _ = QFileDialog.getOpenFileName(
                parent,
                "Open Script",
                str(Path.home()),
                "Python Files (*.py)"
            )
            if file_path:
                try:
                    path = Path(file_path)
                    if path.exists():
                        # Add to recent files
                        file_service = FileService.get_instance()
                        file_service.add_recent_file(str(path), "script")
                        
                        return True, path, ""
                except Exception as e:
                    logger.error(f"ScriptService: Error opening script: {e}")
                    return False, None, str(e)
                    
        return False, None, "No parent widget provided"