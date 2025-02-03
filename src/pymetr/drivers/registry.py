"""
Registry mapping instrument model numbers to their driver implementations 
and connection details.
"""

from typing import Dict, Optional
from enum import Enum, auto

class ConnectionType(Enum):
    """Known connection interface types"""
    VISA = auto()      # VISA (GPIB, USB, some TCP)
    SOCKET = auto()    # Raw TCP socket
    SERIAL = auto()    # Direct serial
    # Add more as needed

DRIVER_REGISTRY: Dict[str, Dict] = {
    # HP Legacy Equipment (typically GPIB/VISA)
    "HP8563A": {
        "module": "drivers.hp8563a",
        "class": "HP8563A",
        "interfaces": [ConnectionType.VISA],
    },
    "HP8564E": {
        "module": "drivers.hp8564e",
        "class": "HP8564E",
        "interfaces": [ConnectionType.VISA],
    },
    "HP8657B": {
        "module": "drivers.hp8657b",
        "class": "HP8657B",
        "interfaces": [ConnectionType.VISA],
    },
    "HP437B": {
        "module": "drivers.hp437b",
        "class": "HP437B",
        "interfaces": [ConnectionType.VISA],
    },

    # Holzworth Equipment (multiple interfaces)
    "HS9001B": {
        "module": "drivers.hs9000",
        "class": "HS9000",
        "interfaces": [
            ConnectionType.VISA,
            ConnectionType.SOCKET,
            ConnectionType.SERIAL
        ],
        "socket_port": 9760,  # For raw socket connections
        "discovery": {
            "udp_port": 30303,  # Microchip stack discovery
            "protocol": "MICROCHIP"
        }
    },
    # Other HS models can reference the same template
    "HS9002B": {"template": "HS9001B"},
    "HS9003B": {"template": "HS9001B"},
    # ... etc
}

def get_driver_info(model: str) -> Dict:
    """
    Get driver information for a given model.
    Handles template references and provides complete driver info.
    
    Args:
        model: Instrument model number
        
    Returns:
        Complete driver configuration dictionary
        
    Raises:
        ValueError: If model not found or template reference invalid
    """
    if model not in DRIVER_REGISTRY:
        raise ValueError(f"No driver registered for model: {model}")
        
    info = DRIVER_REGISTRY[model]
    
    # Handle template references
    if "template" in info:
        template_model = info["template"]
        if template_model not in DRIVER_REGISTRY:
            raise ValueError(f"Invalid template reference: {template_model}")
        # Get template and update with any model-specific overrides
        template = DRIVER_REGISTRY[template_model].copy()
        template.update({k:v for k,v in info.items() if k != "template"})
        return template
        
    return info.copy()

def supports_interface(model: str, interface: ConnectionType) -> bool:
    """Check if model supports a specific interface type"""
    try:
        info = get_driver_info(model)
        return interface in info.get("interfaces", [])
    except ValueError:
        return False

def get_socket_port(model: str) -> Optional[int]:
    """Get socket port for models that support raw socket connections"""
    try:
        info = get_driver_info(model)
        return info.get("socket_port")
    except ValueError:
        return None