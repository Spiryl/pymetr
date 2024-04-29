import logging
logger = logging.getLogger(__name__)

import logging

class Subsystem:
    """
    Base class for creating instrument subsystems, supporting both simple and indexed instantiation, 
    and enabling nested subsystem command prefix cascading.

    Attributes:
        instr (Instrument): Reference to the parent instrument or subsystem. This attribute 
                              facilitates communication with the parent object.
        cmd_prefix (str): The SCPI command prefix associated with the subsystem. This prefix is 
                          used to construct full SCPI commands for property interactions.
    """

    def __init__(self, instr, cmd_prefix="", index=None):
        """
        Initializes a Subsystem instance.

        Args:
            parent (Instrument or Subsystem): The parent instrument or subsystem this instance belongs to.
            cmd_prefix (str): The command prefix specific to this subsystem. It's used as the base for constructing SCPI commands.
            index (int, optional): If provided, it specifies the index of this instance within an indexed subsystem setup. 
                                   This index is appended to the command prefix.
        """
        self.instr = instr
        logger.debug(f"Initializing subsystem with instrument {instr}, prefix {cmd_prefix}, and index {index}")
        # Handle cascading of command prefixes for nested subsystems
        self.cmd_prefix = f"{instr.cmd_prefix}{cmd_prefix}" if hasattr(instr, 'cmd_prefix') else cmd_prefix
        if index is not None:
            self.cmd_prefix += str(index)

    @classmethod
    def build(cls, instr, cmd_prefix, indices=None):
        """
        Class method to instantiate subsystems. This method simplifies the creation process by automatically handling
        both single and indexed instances of subsystems.

        Args:
            parent (Instrument or Subsystem): The parent object to which the new subsystem instance(s) will belong.
            cmd_prefix (str): The SCPI command prefix for the subsystem being created.
            indices (int, optional): The number of indexed instances to create. If None, a single instance is created without indexing.

        Returns:
            Subsystem or list of Subsystem: A single instance of the subsystem if 'indices' is None, 
                                             or a list of indexed subsystem instances if 'indices' is provided.
        """
        if indices is None:
            logger.debug(f"Build method returning single instance")
            # Creating a single instance without indexing
            return cls(instr, cmd_prefix)
        else:
            # Creating multiple indexed instances
            logger.debug(f"Build method creating {indices} instances")
            return [cls(instr, cmd_prefix, index=idx) for idx in range(1, indices + 1)]