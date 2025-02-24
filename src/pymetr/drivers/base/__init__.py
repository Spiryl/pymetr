"""
Base classes for instrument drivers
"""

from .connections import ConnectionInterface, PyVisaConnection, RawSocketConnection
from .instrument import Instrument, SCPIInstrument, Subsystem, ConnectionWorker
from .properties import (
    Property, ValueProperty, SwitchProperty, SelectProperty, 
    DataProperty, DataBlockProperty, PropertyResponse
)
from .sources import Sources
from .visitor import InstrumentVisitor

__all__ = [
    # Connections
    "ConnectionInterface", "PyVisaConnection", "RawSocketConnection",
    # Instruments
    "Instrument", "SCPIInstrument", "Subsystem", "ConnectionWorker",
    # Properties
    "Property", "ValueProperty", "SwitchProperty", "SelectProperty", 
    "DataProperty", "DataBlockProperty", "PropertyResponse",
    # Sources
    "Sources",
    # Visitor
    "InstrumentVisitor"
]