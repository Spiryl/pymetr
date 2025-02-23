import os
import yaml
from typing import Dict

# Determine the path to the YAML file.
# This assumes the YAML file is in the same directory as this module.
REGISTRY_FILE = os.path.join(os.path.dirname(__file__), 'driver_registry.yaml')

def load_registry() -> Dict[str, Dict[str, str]]:
    """Load the driver registry from the YAML file."""
    try:
        with open(REGISTRY_FILE, 'r') as f:
            registry = yaml.safe_load(f)
        return registry
    except Exception as e:
        raise RuntimeError(f"Failed to load driver registry YAML file: {e}")

# Load the registry once at module load time.
_DRIVER_REGISTRY = load_registry()

def get_driver_info(model: str) -> Dict[str, str]:
    """
    Get driver module and class information for a given model.
    Raises ValueError if model not found.
    """
    if model not in _DRIVER_REGISTRY:
        raise ValueError(f"No driver registered for model: {model}")
    return _DRIVER_REGISTRY[model]
