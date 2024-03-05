Quick Start Guide
==================

This guide is designed to quickly acquaint you with the foundational elements necessary for instrument communication using the PyVISA library, understanding the IEEE 488.2 standard, and utilizing the SCPI protocol.

PyVISA and Instrument Communication
------------------------------------

PyVISA is a powerful Python library that provides a unified interface for communication with measurement devices across various interfaces, including GPIB, RS232, USB, and Ethernet. As an open-source library, PyVISA simplifies the process of sending commands to and reading responses from your instruments.

- **Documentation and Source Code:** For comprehensive information and to access the source code, please visit the `PyVISA documentation <https://pyvisa.readthedocs.io/en/latest/>`_ and the `PyVISA GitHub page <https://github.com/pyvisa/pyvisa>`_.

IEEE 488.2 Standard
--------------------

The IEEE 488.2 standard outlines codes, formats, protocols, and common commands for programmable instrumentation, ensuring compatibility across devices from different manufacturers that support the IEEE 488 (GPIB) interface.

- **Further Reading:** For a deeper understanding of the IEEE 488.2 standard and its applications, refer to resources such as `Test & Measurement World <https://www.tmworld.com>`_.

SCPI Protocol
--------------

SCPI, or Standard Commands for Programmable Instruments, is a comprehensive standard that specifies a uniform set of commands for controlling and querying test and measurement devices. This ensures interoperability between devices from different manufacturers, provided they adhere to the SCPI protocol.

- **Learning More:** To explore more about the SCPI standard and its implementation, visit the `Wikipedia Page On SCPI <https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments>`_.

Getting Started with PyVISA
----------------------------

To begin using PyVISA for instrument communication, you will need to install the library and the necessary backend (NI-VISA or pyvisa-py). Here's a quick rundown to get you started:

1. **Installation:** Install PyVISA using pip:

   .. code-block:: bash

      pip install pyvisa

2. **Identify Your Instrument:** Use PyVISA's resource manager to list connected instruments:

   .. code-block:: python

      import pyvisa
      rm = pyvisa.ResourceManager()
      print(rm.list_resources())

3. **Open a Session:** Choose a resource string from the list and open a session to communicate with the instrument:

   .. code-block:: python

      instrument = rm.open_resource('GPIB0::23::INSTR')
      print(instrument.query('*IDN?'))

This quick start guide aims to provide you with the essential knowledge and steps to embark on instrument communication projects, facilitating a smoother transition into developing sophisticated test and measurement applications.
