from pathlib import Path
from typing import Optional, Dict, Union
import os

from PySide6.QtGui import QIcon, QPixmap, QImage
from PySide6.QtCore import QObject, QFile, QIODevice, QResource, QDir

from pymetr.core.logging import logger

class ResourceService(QObject):
    """
    Service for managing application resources like icons, images, and other assets.
    Provides a centralized API for resource loading and caching.
    """
    
    # Singleton instance
    _instance = None
    
    # Resource caches
    _icon_cache: Dict[str, QIcon] = {}
    _pixmap_cache: Dict[str, QPixmap] = {}
    
    @classmethod
    def get_instance(cls):
        """Get the singleton instance of ResourceService."""
        if cls._instance is None:
            cls._instance = ResourceService()
        return cls._instance
    
    def __init__(self):
        """Initialize ResourceService."""
        super().__init__()
        
        # Register resource paths
        self._initialize_resources()
    
    def _initialize_resources(self):
        """Initialize and register resource paths."""
        try:
            # Try to import the compiled resources
            import pymetr.resources_rc
            logger.debug("ResourceService: Loaded compiled resources")
            return
        except ImportError:
            logger.debug("ResourceService: No compiled resources found, using filesystem")
        
        # If no compiled resources, use direct file paths
        # Get the module directory
        import pymetr
        self._base_dir = Path(pymetr.__file__).parent
        
        # Define resource directories
        self._icon_dir = self._base_dir / "ui" / "icons"
        
        logger.debug(f"ResourceService: Using icon directory: {self._icon_dir}")
        
    def get_icon(self, name: str, fallback: Optional[str] = None) -> QIcon:
        """
        Get an icon by name.
        
        Args:
            name: Icon name without extension
            fallback: Optional fallback icon name
            
        Returns:
            QIcon instance
        """
        # Check cache first
        if name in self._icon_cache:
            return self._icon_cache[name]
            
        # Try to load from resources first (if compiled resources are available)
        icon = QIcon(f":/icons/{name}.png")
        
        # If that fails, try to load from filesystem
        if icon.isNull():
            # Try different extensions
            for ext in ['.png', '.svg', '.jpg']:
                path = self._icon_dir / f"{name}{ext}"
                if path.exists():
                    icon = QIcon(str(path))
                    break
            
        # If still null and fallback provided, try fallback
        if icon.isNull() and fallback:
            return self.get_icon(fallback)
            
        # If still null, use a default empty icon
        if icon.isNull():
            logger.warning(f"ResourceService: Icon '{name}' not found")
            # Create an empty icon
            icon = QIcon()
            
        # Cache the result
        self._icon_cache[name] = icon
        
        return icon
    
    def get_pixmap(self, name: str, width: int = 0, height: int = 0) -> QPixmap:
        """
        Get a pixmap by name.
        
        Args:
            name: Pixmap name without extension
            width: Optional width to scale to
            height: Optional height to scale to
            
        Returns:
            QPixmap instance
        """
        # Generate a cache key that includes size
        cache_key = f"{name}_{width}_{height}"
        
        # Check cache first
        if cache_key in self._pixmap_cache:
            return self._pixmap_cache[cache_key]
            
        # Try to load from resources first
        pixmap = QPixmap(f":/images/{name}.png")
        
        # If that fails, try to load from filesystem
        if pixmap.isNull():
            # Try different extensions
            for ext in ['.png', '.svg', '.jpg']:
                path = self._base_dir / "ui" / "images" / f"{name}{ext}"
                if path.exists():
                    pixmap = QPixmap(str(path))
                    break
        
        # Scale if requested
        if not pixmap.isNull() and (width > 0 or height > 0):
            pixmap = pixmap.scaled(
                width if width > 0 else pixmap.width(),
                height if height > 0 else pixmap.height(),
                Qt.KeepAspectRatio,
                Qt.SmoothTransformation
            )
            
        # Cache the result
        self._pixmap_cache[cache_key] = pixmap
        
        return pixmap
    
    def clear_cache(self):
        """Clear all resource caches."""
        self._icon_cache.clear()
        self._pixmap_cache.clear()
        
    def create_qrc_file(self, output_path: Optional[Path] = None) -> bool:
        """
        Create a Qt resource file (.qrc) from the existing icon directory.
        This is useful for generating a resource file that can be compiled.
        
        Args:
            output_path: Path to save the .qrc file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Default output path
            if output_path is None:
                output_path = self._base_dir / "resources.qrc"
                
            # Start the QRC XML content
            qrc_content = '<!DOCTYPE RCC><RCC version="1.0">\n'
            
            # Add icons
            qrc_content += '<qresource prefix="/icons">\n'
            
            for item in os.listdir(self._icon_dir):
                if item.endswith(('.png', '.svg', '.jpg')):
                    qrc_content += f'    <file alias="{item}">ui/icons/{item}</file>\n'
                    
            qrc_content += '</qresource>\n'
            
            # Add other resources if needed...
            
            # Close the XML
            qrc_content += '</RCC>\n'
            
            # Write to file
            with open(output_path, 'w') as f:
                f.write(qrc_content)
                
            logger.info(f"ResourceService: Created QRC file at {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"ResourceService: Error creating QRC file: {e}")
            return False
            
    def compile_resources(self, qrc_path: Optional[Path] = None, output_path: Optional[Path] = None) -> bool:
        """
        Compile a .qrc file into a Python module.
        Requires the 'pyside6-rcc' tool to be available.
        
        Args:
            qrc_path: Path to the .qrc file
            output_path: Path to save the compiled .py file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import subprocess
            
            # Default paths
            if qrc_path is None:
                qrc_path = self._base_dir / "resources.qrc"
                
            if output_path is None:
                output_path = self._base_dir / "resources_rc.py"
                
            # Ensure the .qrc file exists
            if not qrc_path.exists():
                # Try to create it
                if not self.create_qrc_file(qrc_path):
                    return False
            
            # Compile the .qrc file
            cmd = ["pyside6-rcc", "-o", str(output_path), str(qrc_path)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode != 0:
                logger.error(f"ResourceService: Error compiling resources: {result.stderr}")
                return False
                
            logger.info(f"ResourceService: Compiled resources to {output_path}")
            return True
            
        except Exception as e:
            logger.error(f"ResourceService: Error compiling resources: {e}")
            return False