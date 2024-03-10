
from enum import Enum
import re
import logging
import numpy as np
logger = logging.getLogger(__name__)

def command_property(cmd_str, valid_values=None, doc_str="", access="read-write"):
    """
    Factory function to create a property in a subsystem class for interacting with instrument commands.
    Enhanced to accept enums directly for 'valid_values' and allows specifying access type.

    Args:
        cmd_str (str): The base command string for the property.
        valid_values (Enum, optional): Enum of valid values for settable properties.
        doc_str (str): Documentation string for the property.
        access (str, optional): Specifies the access type for the property ('read', 'write', 'read-write').

    Returns:
        property: A property object with custom getter and setter for instrument communication.
    """
    def getter(self):
        # Adjust to include cmd_prefix
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}{'?'}"
        if "read" in access:
            response = self._parent.query(full_cmd_str).strip()
            logger.info(f"Getting {full_cmd_str}, Response = {response}")
            return response.strip()
        else:
            raise AttributeError(f"{full_cmd_str} property is write-only.")

    def setter(self, value):
        # Adjust to include cmd_prefix
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}"
        if "write" in access:
            if isinstance(value, Enum):
                value = value.name  # Use the enum's name instead of its numeric value
            if valid_values is not None and value not in [v.name for v in valid_values]:
                error_msg = f"Invalid value for {full_cmd_str}. Valid values are {[v.name for v in valid_values]}."
                logger.error(error_msg)
                raise ValueError(error_msg)
            logger.info(f"Setting {full_cmd_str} to {value}")
            self._parent.write(f"{full_cmd_str} {value}")
        else:
            raise AttributeError(f"{full_cmd_str} property is read-only.")

    if access == "read":
        return property(fget=getter, doc=doc_str)
    elif access == "write":
        return property(fset=setter, doc=doc_str)
    else:
        return property(fget=getter, fset=setter, doc=doc_str)

def command_options(name, options):
    """
    Dynamically creates an Enum class with given options. This method simplifies the process of defining command parameters,
    making it intuitive and efficient for instrument coders. By using enums, we ensure that the options are not only clearly defined
    but also offer auto-completion support in IDEs, enhancing the coding experience.

    Args:
        name (str): The name of the Enum class to be created. This should be a meaningful and descriptive name related to the command options it represents.
        options (list of str): A list of strings, where each string is a valid option that the command can accept. These options will be the members of the Enum class.

    Returns:
        Enum: A dynamically created Enum class with members corresponding to the provided options.
    """
    return Enum(name, {option: option for option in options})

import logging
import numpy as np
import re

# Setup logging
logger = logging.getLogger(__name__)

def data_property(cmd_str, access='read-write', doc_str="", container=np.array, converter=float, ieee_header=False):
    """
    Factory function to create a data handling property for SCPI commands that deal with data,
    with options to handle IEEE headers for ASCII data, support for writing data, and customization for binary data types.

    Args:
        cmd_str (str): The base command string for the property.
        access (str, optional): Specifies the property access mode ('read', 'write', 'read-write'). Defaults to 'read-write'.
        container (type, optional): Container type to use for the data, e.g., numpy.array. Defaults to numpy.array.
        converter (callable, optional): A function to convert data to/from the desired format. Defaults to float.
        ieee_header (bool, optional): Specifies whether the instrument's response includes an IEEE header for ASCII data. Defaults to False.
        data_type (str, optional): The data type for binary data, following Python's struct module notation. Defaults to 'B' (unsigned byte).

    Returns:
        property: A custom property object for instrument communication.
    """
    def getter(self):
        data_format = self._parent.data_format
        data_type = self._parent.data_type
        full_cmd_str = f"{self.cmd_prefix}{cmd_str}?"  # Include cmd_prefix
        
        try:
            if data_format == 'ASCII' and not ieee_header:
                # Directly use query_ascii_values for ASCII data without IEEE header
                data = self._parent.query_ascii_values(full_cmd_str, converter=converter)
                logger.info(f"Data fetched in ASCII format with {len(data)} elements using PyVISA's automatic handling.")
                return container(data)

            elif data_format == 'ASCII' and ieee_header:
                # Manually handle the IEEE header for ASCII data
                raw_response = self._parent.query(full_cmd_str)
                header_match = re.match(r'#(\d)(\d+)\s', raw_response)
                if header_match:
                    num_digits = int(header_match.group(1))
                    length_of_data_block = int(header_match.group(2)[:num_digits])
                    data_start = num_digits + len(str(length_of_data_block)) - 2
                    ascii_data = raw_response[data_start:].strip().split(',')
                    data = container([converter(val) for val in ascii_data])
                    logger.info(f"Data fetched in ASCII format with {len(data)} elements using manual IEEE header parsing.")
                    return data
                else:
                    raise ValueError("Failed to parse IEEE header from ASCII response.")

            elif data_format == 'BINARY':
                # Use query_binary_values for binary data, specifying the data type dynamically
                data = self._parent.query_binary_values(full_cmd_str, datatype=data_type, is_big_endian=False)
                logger.info(f"Data fetched in binary format with {len(data)} elements using PyVISA's automatic handling.")
                return container(data)

        except Exception as e:
            logger.error(f"Exception while fetching data: {e}")
            raise

    def setter(self, value):
        if access not in ['write', 'read-write']:
            raise AttributeError(f"{cmd_str} property is read-only.")

        try:
            data_format = self._parent.data_format
            data_type = self._parent.data_type
            full_cmd_str = f"{self.cmd_prefix}{cmd_str}"  # Include cmd_prefix
            logger.info(f"Sending data with command: {full_cmd_str}")

            if data_format == 'ASCII':
                # Use write_ascii_values for ASCII data
                self._parent.write_ascii_values(full_cmd_str, value, converter=str)
                logger.info(f"Data sent in ASCII format: {value}")
            elif data_format == 'BINARY':
                # Use write_binary_values for binary data, specifying the data type dynamically
                self._parent.write_binary_values(full_cmd_str, value, datatype=data_type)
                logger.info(f"Data sent in binary format: {value}")
        except Exception as e:
            logger.error(f"Failed to send data with command {full_cmd_str}: {e}")
            raise e

    return property(fget=getter if 'read' in access else None,
                    fset=setter if 'write' in access else None,
                    doc=doc_str)


# def data_property(cmd_str, access='read-write', doc_str="", container=np.array, converter=float):
#     """
#     Factory function to create a data handling property for SCPI commands that deal with data.

#     Args:
#         cmd_str (str): The base command string for the property.
#         access (str, optional): Specifies the property access mode ('read', 'write', 'read-write'). Defaults to 'read-write'.
#         container (type, optional): Container type to use for the data, e.g., numpy.array. Defaults to numpy.array.
#         converter (callable, optional): A function to convert data to/from the desired format. Defaults to float.

#     Returns:
#         property: A custom property object for instrument communication.
#     """
#     def getter(self):
#         data_format = self._parent.data_format
#         full_cmd_str = f"{self.cmd_prefix}{cmd_str}?"  # Include cmd_prefix
#         logger.info(f"Fetching data with command: {full_cmd_str}, format set to: {data_format}")

#         try:
#             raw_response = self._parent.query(full_cmd_str)
#             logger.info(f"Raw response received: {raw_response[:100]}")  # Show start of the response

#             if data_format == 'ASCII':
#                 # IEEE header: #8<length_of_data_block><data_block>
#                 header_match = re.match(r'#(\d)(\d{8})', raw_response)
#                 if header_match:
#                     num_digits = int(header_match.group(1))  # Should always be 8 based on your documentation
#                     length_of_data_block = int(header_match.group(2))  # The next 8 digits give the length
                    
#                     data_start = 2 + num_digits  # Skip over '#' and '8'
#                     ascii_data = raw_response[data_start:data_start+length_of_data_block]
#                     logger.info(f"Extracted ASCII data: {ascii_data[:100]}")

#                     # Assuming the data is comma-separated, convert to the desired numeric type
#                     data = container([converter(val) for val in ascii_data.split(',') if val.strip()])
#                     logger.info(f"Data converted to container with {len(data)} elements.")
#                     return data
#                 else:
#                     error_msg = "Failed to parse IEEE header from ASCII response."
#                     logger.error(error_msg)
#                     raise ValueError(error_msg)

#             elif data_format == 'BYTE':
#                 # For BYTE format, you expect binary data after the IEEE header
#                 header_match = re.match(r'#(\d)(\d+)', raw_response)
#                 if header_match:
#                     num_digits = int(header_match.group(1))
#                     length_of_data_block = int(header_match.group(2)[:num_digits])
                    
#                     # Calculate the starting point of the actual binary data
#                     data_start = 2 + num_digits + len(str(length_of_data_block))
#                     # The raw_response here is expected to be binary, so adjust your query method if needed
#                     binary_data = raw_response[data_start:].encode('latin-1')  # Use 'latin-1' to keep binary data intact
                    
#                     # Convert binary data to numpy array
#                     data = np.frombuffer(binary_data, dtype=np.uint8)
#                     logger.info(f"Data converted to container with {len(data)} elements.")
#                     return data

#         except Exception as e:
#             logger.error(f"Exception while fetching data: {e}")
#             raise

#     def setter(self, value):
#         data_format = self._parent.data_format
#         full_cmd_str = f"{self.cmd_prefix}{cmd_str}"  # Include cmd_prefix
#         logger.info(f"Sending data with command: {full_cmd_str}")
#         try:
#             if access in ['write', 'read-write']:
#                 if data_format == 'ASCII':
#                     self._parent.write_ascii_values(full_cmd_str, value, container=container, converter=converter)
#                     logger.info(f"Data sent in ASCII format: {value}")
#                 elif data_format == 'BYTE':
#                     self._parent.write_binary_values(full_cmd_str, value, container=container)
#                     logger.info(f"Data sent in binary format: {value}")
#             else:
#                 raise AttributeError(f"{full_cmd_str} property is read-only.")
#         except Exception as e:
#             logger.error(f"Failed to send data with command {full_cmd_str}: {e}")
#             raise e

#     return property(fget=getter if 'read' in access else None,
#                     fset=setter if 'write' in access else None,
#                     doc=doc_str)

class Subsystem:
    """
    Base class for creating instrument subsystems. This class is designed to be inherited by specific subsystem classes,
    providing them with the ability to send queries and commands to the instrument.

    This class should not be instantiated directly but extended by specific instrument subsystems.
    """

    def __init__(self, parent, cmd_prefix=""):
        """
        Initializes the subsystem with a reference to its parent instrument and an optional command prefix.

        Args:
            parent (Instrument): The parent instrument object this subsystem belongs to.
            cmd_prefix (str, optional): The command prefix for this subsystem. Defaults to an empty string.
        """
        self._parent = parent
        self.cmd_prefix = cmd_prefix
