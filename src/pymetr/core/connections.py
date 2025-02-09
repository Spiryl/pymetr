from typing import Dict, Optional, List, Any
import socket
from abc import ABC, abstractmethod
from dataclasses import dataclass
from PySide6.QtCore import QObject, Signal, Qt
import pyvisa

from pymetr.core.registry import ConnectionType
from pymetr.core.logging import logger

@dataclass
class ConnectionConfig:
    """Connection configuration parameters"""
    type: ConnectionType
    resource: str
    timeout: float = 5.0
    read_termination: str = '\n'
    write_termination: str = '\n'
    encoding: str = 'ascii'
    extra_params: Dict[str, Any] = None

class ConnectionInterface(QObject):
    """Base class for all connection interfaces."""
    
    # Signals
    data_received = Signal(bytes)
    error_occurred = Signal(str)
    
    def __init__(self, config: ConnectionConfig):
        super().__init__()
        self.config = config
        self._is_open = False
        
    @property
    def is_open(self) -> bool:
        return self._is_open
        
    @abstractmethod
    def open(self) -> None:
        """Open the connection."""
        pass
        
    @abstractmethod
    def close(self) -> None:
        """Close the connection."""
        pass
        
    @abstractmethod
    def write(self, data: str) -> None:
        """Write data to the connection."""
        pass
        
    @abstractmethod
    def read(self) -> str:
        """Read data from the connection."""
        pass
        
    @abstractmethod
    def query(self, command: str) -> str:
        """Send a query and get response."""
        pass

class VisaConnection(ConnectionInterface):
    """VISA connection implementation."""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.rm = pyvisa.ResourceManager()
        self.instrument = None
        
    def open(self) -> None:
        try:
            self.instrument = self.rm.open_resource(self.config.resource)
            self.instrument.timeout = self.config.timeout * 1000  # Convert to ms
            self.instrument.read_termination = self.config.read_termination
            self.instrument.write_termination = self.config.write_termination
            self._is_open = True
            logger.debug(f"Opened VISA connection to {self.config.resource}")
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise
            
    def close(self) -> None:
        if self.instrument:
            self.instrument.close()
            self._is_open = False
            
    def write(self, data: str) -> None:
        try:
            self.instrument.write(data)
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise
            
    def read(self) -> str:
        try:
            data = self.instrument.read()
            self.data_received.emit(data.encode(self.config.encoding))
            return data
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise
            
    def query(self, command: str) -> str:
        try:
            return self.instrument.query(command)
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise

class SocketConnection(ConnectionInterface):
    """Raw socket connection implementation."""
    
    def __init__(self, config: ConnectionConfig):
        super().__init__(config)
        self.socket = None
        
    def open(self) -> None:
        try:
            host, port = self._parse_resource()
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.settimeout(self.config.timeout)
            self.socket.connect((host, port))
            self._is_open = True
            logger.debug(f"Opened socket connection to {host}:{port}")
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise
            
    def close(self) -> None:
        if self.socket:
            self.socket.close()
            self._is_open = False
            
    def write(self, data: str) -> None:
        try:
            encoded = data.encode(self.config.encoding)
            if not data.endswith(self.config.write_termination):
                encoded += self.config.write_termination.encode(self.config.encoding)
            self.socket.sendall(encoded)
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise
            
    def read(self) -> str:
        try:
            data = b""
            term = self.config.read_termination.encode(self.config.encoding)
            
            while True:
                chunk = self.socket.recv(4096)
                if not chunk:
                    break
                data += chunk
                if term in data:
                    break
                    
            self.data_received.emit(data)
            return data.decode(self.config.encoding)
        except Exception as e:
            self.error_occurred.emit(str(e))
            raise
            
    def query(self, command: str) -> str:
        self.write(command)
        return self.read()
        
    def _parse_resource(self) -> tuple[str, int]:
        """Parse resource string into host and port."""
        if "::" in self.config.resource:  # VISA-style
            parts = self.config.resource.split("::")
            return parts[1], int(parts[2])
        else:  # host:port style
            host, port = self.config.resource.split(":")
            return host.strip(), int(port)

class ConnectionFactory:
    """Creates appropriate connection interface based on type."""
    
    @staticmethod
    def create_connection(config: ConnectionConfig) -> ConnectionInterface:
        """
        Create a connection instance.
        
        Args:
            config: Connection configuration
            
        Returns:
            Connection interface instance
            
        Raises:
            ValueError: If connection type not supported
        """
        if config.type == ConnectionType.VISA:
            return VisaConnection(config)
        elif config.type == ConnectionType.SOCKET:
            return SocketConnection(config)
        else:
            raise ValueError(f"Unsupported connection type: {config.type}")
    
    @staticmethod
    def create_from_resource(resource: str) -> ConnectionInterface:
        """
        Create connection from a resource string.
        Determines type automatically.
        
        Args:
            resource: Resource identifier string
            
        Returns:
            Connection interface instance
        """
        if resource.startswith("TCPIP") and "SOCKET" in resource:
            config = ConnectionConfig(
                type=ConnectionType.SOCKET,
                resource=resource
            )
        else:
            config = ConnectionConfig(
                type=ConnectionType.VISA,
                resource=resource
            )
        return ConnectionFactory.create_connection(config)