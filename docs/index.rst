Pymetr Package Overview
=======================

Purpose
-------
Pymetr is a Python package designed to abstract the complexities involved in controlling and interacting with scientific and industrial instruments. By leveraging the power of Pythonic object-oriented programming, Pymetr provides a streamlined approach for engineers and researchers to create automated test scripts without the tedium of managing low-level SCPI command strings. At its core, Pymetr simplifies instrument control through intuitive factory functions, a base instrument class, and a subsystem class.

System Dependencies
-------------------
- **Python Version**: 3.12.0
- **numpy**: Efficient numerical computations
- **pyvisa**: Instrument communication
- **pyside6**: Qt bindings and GUI application development
- **pyqtgraph**: High-performance scientific plotting and controls

Base Classes
------------
The **Instrument** class forms the backbone of Pymetr, offering a high-level interface for SCPI-compliant devices. It encapsulates connection management, command transmission, and data retrieval, significantly reducing the boilerplate code typically associated with instrument control. Key features include:

- Connection handling via PyVISA
- ASCII and binary data query methods
- SCPI command support for operational control (e.g., reset, clear status)

The **Subsystem** class allows for the creation of instrument-specific subsystems, which can be nested and have properties directly mapped to SCPI commands. This class facilitates the organization and encapsulation of instrument functionalities into coherent units.

Factory Functions
-----------------
Pymetr introduces several factory functions to dynamically generate properties for instrument subsystems. These functions are designed to handle common SCPI patterns, such as switching states, setting numerical values, and selecting from enumerated options. Factory functions include:

- **switch_property**: For boolean switches, mapping user-friendly values to "ON"/"OFF" commands.
- **value_property**: For numerical values, with support for range checking.
- **select_property**: For selecting from enumerated options, simplifying interaction with pre-defined instrument settings.
- **data_property**: For handling instrument data in ASCII or binary formats, including IEEE header parsing.

GUI Builder
-----------
The package also offers an **instrument_gui** utility, which automatically generates basic graphical interfaces for instrument control, data acquisition, and plotting. This feature leverages the properties and subsystems defined in the instrument model to provide a quick and easy way to interact with instruments without writing additional GUI code.

Conclusion
----------
Pymetr empowers developers and engineers with a highly abstracted, yet flexible, framework for instrument control, making it easier to focus on the experimental and testing objectives rather than the intricacies of instrument communication.

.. note:: This package requires PyVISA as a backend for communication with instruments, ensuring wide compatibility with various types of test equipment.

Todo
----

- Documentation/graphics
- Continue GUI development with trace controls and instrument selection
- Refactor Instrument GUI acquisition thread.
- Start spectrum analyzer class.
- Start power meter class.

.. toctree::
   :maxdepth: 2
   :caption: Contents:
   
   quickstart
   bible
   instruments
   subsystem_theory
   properties
   subsystem_example
   instrument_gui
   oscilloscope
   packaging
   doc-build
   sphinx
   logging
   unit-test
   api
