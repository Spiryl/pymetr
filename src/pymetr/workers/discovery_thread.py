# src/pymetr/workers/discovery_thread.py
from PySide6.QtCore import QThread, Signal

from pymetr.logging import logger
from pymetr.drivers.connections import RawSocketConnection, PyVisaConnection

class DiscoveryThread(QThread):
    discovered = Signal(dict)  # Emits final discovered devices
    error = Signal(str)        # Emits any errors
    
    def __init__(self):
        super().__init__()
        self.discovered_devices = {}
        # Keep reference to connection signals
        RawSocketConnection._signals.instrument_found.connect(self._on_instrument_found)
        PyVisaConnection._signals.instrument_found.connect(self._on_instrument_found)

    def _on_instrument_found(self, device_info: dict):
        """Handle individual device discoveries"""
        model = device_info.get('model')
        if model:
            self.discovered_devices[model] = device_info

    def run(self):
        try:
            # Run discoveries
            visa_devices = PyVisaConnection.list_instruments()
            socket_devices = RawSocketConnection.list_instruments(timeout=2.0)
            
            # Combine results if not already in discovered_devices
            for model, info in visa_devices.items():
                if model not in self.discovered_devices:
                    self.discovered_devices[model] = info
                    
            for model, info in socket_devices.items():
                if model not in self.discovered_devices:
                    self.discovered_devices[model] = info
                    
        except Exception as e:
            self.error.emit(str(e))
        finally:
            # Always emit results, even if empty
            self.discovered.emit(self.discovered_devices)

    def stop(self):
        """Clean shutdown"""
        self.wait()  # Wait for thread to finish
        
    def __del__(self):
        """Ensure thread is stopped on deletion"""
        self.stop()
