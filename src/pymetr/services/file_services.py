from pathlib import Path
from typing import Dict, Any, Optional, Tuple
from PySide6.QtWidgets import QWidget, QFileDialog
import yaml

from pymetr.core.logging import logger
from pymetr.models.test import TestSuite, TestScript

class FileService:
    """Service for importing/exporting model data and handling files."""
    
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
            return True
            
        except Exception as e:
            logger.error(f"Error exporting model data: {e}")
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
            
            return FileService._import_model(data, state)
            
        except Exception as e:
            logger.error(f"Error importing model data: {e}")
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
            logger.error(f"Error importing model: {e}")
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
                    logger.error(f"Error opening suite: {e}")
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
            logger.error(f"Error saving suite: {e}")
            return False, None, str(e)
            
        return False, None, "Operation cancelled"