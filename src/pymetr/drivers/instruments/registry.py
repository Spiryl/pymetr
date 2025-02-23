"""
Registry mapping instrument model numbers to their driver implementations.
"""

from typing import Dict

DRIVER_REGISTRY: Dict[str, Dict[str, str]] = {
    "HP8563A": {
        "module": "drivers.hp8563a",
        "class": "HP8563A"
    },
    "HP8564E": {
        "module": "drivers.hp8564e",
        "class": "HP8564E"
    },
    "HP8657B": {
        "module": "drivers.hp8657b",
        "class": "HP8657B"
    },
    "HP437B": {
        "module": "drivers.hp437b",
        "class": "HP437B"
    },
    "HS9001B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9002B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9003B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9004B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9005B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9006B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9007B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9008B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9009B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9010B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9011B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9012B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9013B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9014B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9015B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    },
    "HS9016B": {
        "module": "drivers.hs9000.py",
        "class": "HS9000"
    }
    # Add more models as needed
}

def get_driver_info(model: str) -> Dict[str, str]:
    """
    Get driver module and class information for a given model.
    Raises ValueError if model not found.
    """
    if model not in DRIVER_REGISTRY:
        raise ValueError(f"No driver registered for model: {model}")
    return DRIVER_REGISTRY[model]