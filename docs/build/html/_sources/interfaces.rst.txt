Interfaces Module
=================

The ``interfaces`` module within the ``pyinstrument`` package provides the infrastructure to implement various communication interfaces for instruments. It includes a base class for defining interfaces and derived classes for specific interface types such as VISA or TCP/IP.

.. note:: This module uses the factory design pattern to create instances of interfaces dynamically based on the requirements.

InstrumentInterface
-------------------

The ``InstrumentInterface`` class is an abstract base class that defines the required methods for any communication interface.

.. autoclass:: pyinstrument.interfaces.InstrumentInterface
   :members:
   :undoc-members:
   :show-inheritance:

The interface class enforces implementation of the following methods:

- ``open``: Initializes the communication channel.
- ``close``: Terminates the communication channel.
- ``write``: Transmits a command to the instrument.
- ``read``: Receives data from the instrument.
- ``query``: Executes a write followed by a read for streamlined communication.

Factory Method
--------------

A key feature of the module is the factory method ``create_interface``, which facilitates the creation of interface objects.

.. code-block:: python

   # Creating a VISA interface
   visa_interface = InstrumentInterface.create_interface('pyvisa', resource_string)

   # Creating a TCP/IP interface
   tcpip_interface = InstrumentInterface.create_interface('tcpip', '192.168.1.100:5025')

Interface Classes
-----------------

Derived classes implement specific types of interfaces.

.. autoclass:: pyinstrument.interfaces.VisaInterface
   :members:
   :undoc-members:
   :show-inheritance:

.. autoclass:: pyinstrument.interfaces.TCPIPInterface
   :members:
   :undoc-members:
   :show-inheritance:

Each interface class provides tailored methods for establishing connections and communicating using the respective protocols.

Graphical Representation of the Model
-------------------------------------

.. graphviz::

   digraph interfaces {
       node [shape=record, fontname=Helvetica, fontsize=10];
       InstrumentInterface [label="{InstrumentInterface|+ open()\l+ close()\l+ write(command: str)\l+ read(): str\l+ query(command: str): str\l|create_interface(interface_type: str, resource_string: str)}"];
       VisaInterface [label="{VisaInterface|...}"];
       TCPIPInterface [label="{TCPIPInterface|...}"];

       InstrumentInterface -> VisaInterface;
       InstrumentInterface -> TCPIPInterface;
   }

The above diagram illustrates the relationship between the ``InstrumentInterface`` and its derived classes. The ``InstrumentInterface`` acts as the blueprint, while ``VisaInterface`` and ``TCPIPInterface`` provide the concrete implementations for their respective communication protocols.