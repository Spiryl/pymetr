Instrument Control Library
==========================

The ``Instruments Library`` is engineered as the foundational framework for interfacing and commanding a wide range of test and measurement devices. At the core of this framework is the ``Instrument`` base class, which interfaces with the PyVISA library to support various communication protocols and instrument-specific operations.

Instrument Base Class
---------------------

The ``Instrument`` base class unifies the API for interacting with instruments of diverse nature. It utilizes PyVISA as the backend for communication, covering standard protocols such as GPIB, RS232, USB, and Ethernet. It is designed to be extended for custom interfaces and communication protocols.

**Key Features:**

- Standardized management of connections (open/close).
- Execution of SCPI-compliant and customized commands (read/write).
- Immediate query execution with built-in response processing.
- Reliable instrument identification and status management.

Class Diagram
-------------

The class diagram illustrates the relationship between the PyVISA backend and the ``Instrument`` class. It highlights how the ``Instrument`` class extends PyVISA's functionality with additional methods for controlling measurement devices.

.. graphviz::

   digraph architecture {
      node [shape=record, fontname=Helvetica, fontsize=10];
      
      PyVISA [label="{PyVISA|+ open_resource()\l+ list_resources()\l+ read()\l+ write()\l...}"]
      Instrument [label="{Instrument|+ identity(): str\l+ status(): str\l+ reset()\l+ clear_status()\l...}"]

      PyVISA -> Instrument [arrowhead="onormal", style="dashed"]

      label="Instrument Class Architecture";
      fontsize=12;
   }

Utilizing the Library
---------------------

Below is a succinct example illustrating the application of the library within a Python script for fundamental instrument interaction:

.. code-block:: python

   from pymetr.instruments import Instrument

   # Instrument discovery and selection
   instrument_address = Instrument.select_resources()
   my_instrument = Instrument(instrument_address)
   my_instrument.open()

   # Engaging with the instrument
   print(my_instrument.identity())
   print(my_instrument.query('MEAS:VOLT:DC?'))

Instrument Class API
--------------------

.. autoclass:: pymetr.instruments.Instrument
   :members:
   :undoc-members:
   :show-inheritance:
