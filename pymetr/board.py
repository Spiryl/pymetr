import logging
logger = logging.getLogger(__name__)

from enum import Enum
import re
import numpy as np

# Board Base Class
class Board:
    def __init__(self, system_address):
        self.system_address = system_address
        # PyVISA resource initialization logic here

    def read_register(self, address, size):
        # Implement read logic using PyVISA
        pass

    def write_register(self, address, value, size):
        # Implement write logic using PyVISA
        pass

# Module Base Class
class Module:
    def __init__(self, board, major_offset):
        self.board = board
        self.major_offset = major_offset
        # Initialize module-specific properties here