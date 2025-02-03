# src/pymetr/actions/registry.py
from typing import Dict, Type
from pathlib import Path
import importlib.util
import inspect
from .commands import Command
from pymetr.logging import logger

class CommandRegistry:
    """Auto-discovers and registers command classes"""
    
    _instance = None
    _commands: Dict[str, Type[Command]] = {}

    def __new__(cls):
        logger.info("Creating new CommandRegistry instance")
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialize()
        return cls._instance
    
    def _initialize(self):
        """Load all command classes from the actions directory"""
        actions_dir = Path(__file__).parent
        logger.info(f"Scanning for commands in directory: {actions_dir}")
        
        # Determine the package path
        package_path = "pymetr.actions."
        logger.info(f"Using package path: {package_path}")
        
        py_files = list(actions_dir.glob("*.py"))
        logger.info(f"Found Python files: {[f.name for f in py_files]}")
        
        for py_file in py_files:
            if py_file.stem in ['__init__', 'registry', 'commands']:
                continue
                
            try:
                # Import using the package path
                module_name = package_path + py_file.stem
                logger.info(f"Attempting to import module: {module_name}")
                
                module = importlib.import_module(module_name)
                
                # Find all Command subclasses
                members = inspect.getmembers(module)
                logger.info(f"Module members in {py_file.name}: {[name for name, _ in members]}")
                
                for name, obj in members:
                    if (inspect.isclass(obj) and 
                        issubclass(obj, Command) and 
                        obj != Command):
                        # Convert CamelCase to snake_case for action_id
                        action_id = ''.join([f'_{c.lower()}' if c.isupper() else c 
                                           for c in name]).lstrip('_')
                        action_id = action_id.replace('_command', '')
                        self._commands[action_id] = obj
                        logger.info(f"Successfully registered command '{action_id}' -> {obj.__name__}")
                            
            except Exception as e:
                logger.error(f"Error loading commands from {py_file}: {e}", exc_info=True)
        
        logger.info(f"Command registration complete. Found {len(self._commands)} commands:")
        for action_id, command_class in self._commands.items():
            logger.info(f"  {action_id} -> {command_class.__name__}")
    
    @classmethod
    def get_command(cls, action_id: str) -> Type[Command]:
        """Get command class for an action_id"""
        command = cls._commands.get(action_id)
        if not command:
            logger.error(f"No command found for action_id: {action_id}")
            logger.debug(f"Available commands: {list(cls._commands.keys())}")
        return command
    
    @classmethod
    def get_available_commands(cls) -> Dict[str, Type[Command]]:
        """Get all registered commands"""
        return cls._commands.copy()