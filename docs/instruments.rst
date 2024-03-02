Instrument Control Library
==========================

The ``Instrument Control Library`` forms the backbone of a flexible system designed to communicate with and control a variety of test and measurement hardware. From the foundational ``Instrument`` base class to the specialized interface classes and modular subsystems, this library streamlines the development and execution of instrument control applications.

Instrument Base Class
---------------------

At the heart of the library is the ``Instrument`` base class, providing a unified API for interaction with diverse instruments. Leveraging PyVISA for backend communication, it supports standard protocols like GPIB, RS232, USB, and Ethernet, while also offering a path to integrate more specialized interfaces such as PXI hardware drivers and LXI protocols.

.. autoclass:: pyinstrument.instruments.Instrument
   :members:
   :undoc-members:
   :show-inheritance:

Key Features:
- Standardized connection management (open/close).
- Reading and writing capabilities for SCPI-compliant and custom commands.
- Query execution with response handling.
- Instrument identification and status management.

Class Diagram
-------------

.. graphviz::

   digraph instrument_hierarchy {
      node [shape=record, fontname=Helvetica, fontsize=10];
      
      Instrument [label="{Instrument|+ open()\l+ close()\l+ write(command: str)\l+ read(): str\l+ query(command: str): str\l}"]
      SCPIInstrument [label="{SCPIInstrument}"]
      VXIInstrument [label="{VXIInstrument}"]
      LXIInstrument [label="{LXIInstrument}"]

      Instrument -> SCPIInstrument [arrowhead="onormal"]
      Instrument -> VXIInstrument [arrowhead="onormal"]
      Instrument -> LXIInstrument [arrowhead="onormal"]

      label="Instrument Class Hierarchy";
      fontsize=12;
   }

Instrument Subsystems
---------------------

The library's design emphasizes modularity through instrument subsystems. These subsystems allow for targeted control and testing of specific instrument functionalities, facilitating a granular approach to instrument interaction.

Subsystem Integration:

.. graphviz::

   digraph subsystem_relationship {
      node [shape=record, fontname=Helvetica, fontsize=10];
      
      Instrument [label="{Instrument|+ sync()\l}"]
      TimebaseSubsystem [label="{TimebaseSubsystem}"]
      TriggerSubsystem [label="{TriggerSubsystem}"]
      MeasurementSubsystem [label="{MeasurementSubsystem}"]

      Instrument -> TimebaseSubsystem [arrowhead="onormal"]
      Instrument -> TriggerSubsystem [arrowhead="onormal"]
      Instrument -> MeasurementSubsystem [arrowhead="onormal"]

      { rank=same; TimebaseSubsystem; TriggerSubsystem; MeasurementSubsystem; }

      label="Instrument Subsystem Relationships";
      fontsize=12;
   }

Interactive CLI
---------------

The library includes an interactive CLI for direct engagement with instruments. This tool is invaluable for rapid testing, debugging, and hands-on learning, providing a straightforward interface for real-time instrument control.

Example Usage:

.. code-block:: python

   if __name__ == "__main__":
       # CLI functionality detailed here

Using the Library
-----------------

Below is a simple example showcasing the library's usage within a Python environment:

.. code-block:: python

   from pyinstrument import SCPIInstrument

   # Discover and select instruments
   instrument_address = SCPIInstrument.select_resources()
   my_instrument = SCPIInstrument(instrument_address, interface_type='pyvisa')
   my_instrument.open()

   # Basic instrument interaction
   print(my_instrument.query('*IDN?'))
   my_instrument.write('MEAS:VOLT:DC?')
   print(my_instrument.read())

   # Close the connection
   my_instrument.close()
