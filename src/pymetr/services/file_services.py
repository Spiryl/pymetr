# services/file_service.py
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from pymetr.core.logging import logger 

class FileService:
    """Service for importing/exporting model data."""
    
    @staticmethod
    def export_model_data(model_id: str, state, path: Path) -> bool:
        """Export model and its children to YAML."""
        try:
            model = state.get_model(model_id)
            if not model:
                return False
                
            data = {
                'type': type(model).__name__,
                'properties': model._properties,
                'children': []
            }
            
            # Export children recursively
            for child in state.get_children(model_id):
                child_data = FileService._export_model(child, state)
                data['children'].append(child_data)
                
            # Write to file
            with open(path, 'w') as f:
                yaml.dump(data, f)
            return True
            
        except Exception as e:
            logger.error(f"Error exporting model data: {e}")
            return False

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