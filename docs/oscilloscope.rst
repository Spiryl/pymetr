Oscilloscope Extension
======================

The `Oscilloscope` class serves as an orchestrator for the complex interplay of its various subsystems, each encapsulated within its own class. Unlike a classical inheritance structure, the ``Oscilloscope`` class does not serve as a superclass from which subsystems inherit. Instead, it aggregates these subsystems—such as ``Trigger``, ``Timebase``, ``Waveform``, ``WaveGen``, ``Acquire``, and ``Channel``—as components, illustrating a composition-based architecture.

This design philosophy allows for a high degree of modularity, enabling each subsystem to be developed, tested, and modified independently while the ``Oscilloscope`` class provides a cohesive and unified interface for the user. The result is a robust and scalable structure, where the complexity of the instrument's functionalities is managed with grace and precision.

The ``pymetr`` package reflects this architecture, segregating related functionalities into dedicated subsystem classes. This not only enhances code organization but also fosters intuitive and object-oriented control over each aspect of the oscilloscope. Below is a visual representation of the ``Oscilloscope`` class composition:

.. graphviz::

   digraph architecture {
      node [shape=record fontname=Helvetica fontsize=10];
      rankdir=UD;
      
      PyVisa [label="{PyVisa|+ open()\l+ close()\l+ write(command: str)\l+ read(): str\l+ query(command: str): str\l}"];
      
      Instrument [label="{Instrument|+ identity()\l+ reset()\l+ status()\l}"];
      Oscilloscope [label="{Oscilloscope|+ run()\l+ stop()\l+ single()\l+ autoscale()\l}"];
      
      Acquire [label="{Acquire|+ _mode: Mode\l+ _type: Type\l}"];
      Channel [label="{Channel|+ coupling: Coupling\l+ display: DisplayState\l}"];
      Timebase [label="{Timebase|+ mode: Mode\l+ position: float\l}"];
      Trigger [label="{Trigger|+ mode: Mode\l+ level: float\l}"];
      Waveform [label="{Waveform|+ format: Format\l+ source: Source\l}"];
      WaveGen [label="{WaveGen|+ function: Function\l+ output: Output\l}"];
      
      PyVisa -> Instrument [arrowhead="onormal", style="dashed"];
      Instrument -> Oscilloscope [arrowhead="onormal", style="dashed"];
      
      Oscilloscope -> Acquire [arrowhead="odiamond"];
      Oscilloscope -> Channel [arrowhead="odiamond"];
      Oscilloscope -> Timebase [arrowhead="odiamond"];
      Oscilloscope -> Trigger [arrowhead="odiamond"];
      Oscilloscope -> Waveform [arrowhead="odiamond"];
      Oscilloscope -> WaveGen [arrowhead="odiamond"];
      
      {rank=same; Acquire Channel Timebase Trigger Waveform WaveGen}
   }


Root Functions
--------------------

The ``Oscilloscope`` class also includes root-level functions which do not below to a subsystem. These include functions like `run`, `stop`, `single`, and `autoscale` as well a high level data acquisition and processing specific further abstracting the use of the instrument.

.. note:: The ``Oscilloscope`` class is designed with the user in mind, abstracting the complexities of the oscilloscope operation and providing a user-friendly interface that reflects the natural workflow of an engineer or technician working with the instrument.

Getting Started with the Oscilloscope Class
-------------------------------------------

To begin using the ``Oscilloscope`` class, first ensure that PyVISA is installed and properly configured in your environment. Here's a quick rundown on creating an instance of the ``Oscilloscope`` and running basic operations:

.. code-block:: python

   from pymetr.oscilloscope import Oscilloscope

   # Replace with your oscilloscope's VISA resource string
   resource_string = 'TCPIP0::192.168.1.111::hislip0::INSTR'
   osc = Oscilloscope(resource_string)
   osc.open()
   print(f"Identification string: '{osc.identity()}'")
   osc.close()
