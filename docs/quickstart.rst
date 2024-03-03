Quick Start Guide
==================

PyVISA and Instrument Communication
------------------------------------

PyVISA is an open-source Python library that enables you to control all kinds of measurement devices independently of the interface (e.g., GPIB, RS232, USB, Ethernet). For detailed documentation and source code, visit the `PyVISA documentation <https://pyvisa.readthedocs.io/en/latest/>`_ and the `PyVISA GitHub page <https://github.com/pyvisa/pyvisa>`_.

IEEE 488.2 Standard
--------------------

IEEE 488.2 is a standard for programmable instrumentation that defines codes, formats, protocols, and common commands for use with all IEEE 488-compatible devices. For more information on the IEEE 488.2 standard, you can refer to a reputable site such as `Test & Measurement World <https://www.tmworld.com>`_.

SCPI Protocol
--------------

SCPI (Standard Commands for Programmable Instruments) defines a standard for syntax and commands to be used in controlling programmable test and measurement devices. This standard ensures that a device from one manufacturer can be controlled and queried in a predictable way using commands from a device of another manufacturer, provided they both adhere to the SCPI standard.
`Wikipedia Page On SCPI <https://en.wikipedia.org/wiki/Standard_Commands_for_Programmable_Instruments>`_


Resource Strings and Instrument Identification
-----------------------------------------------

Resource strings are unique identifiers that PyVISA uses to communicate with instruments. They typically contain information about the interface type, the address, and other necessary details for making a connection.