Oscilloscope Extension
======================

The ``Oscilloscope`` class serves as an orchestrator for the complex interplay of its various subsystems, each encapsulated within its own class. Unlike a classical inheritance structure, the ``Oscilloscope`` class does not serve as a superclass from which subsystems inherit. Instead, it aggregates these subsystems—such as ``Trigger``, ``Timebase``, ``Waveform``, ``WaveGen``, ``Acquire``, and ``Channel``—as components, illustrating a composition-based architecture.

This design philosophy allows for a high degree of modularity, enabling each subsystem to be developed, tested, and modified independently while the ``Oscilloscope`` class provides a cohesive and unified interface for the user. The result is a robust and scalable structure, where the complexity of the instrument's functionalities is managed with grace and precision.

The ``pymetr`` package reflects this architecture, segregating related functionalities into dedicated subsystem classes. This not only enhances code organization but also fosters intuitive and object-oriented control over each aspect of the oscilloscope. Below is a visual representation of the ``Oscilloscope`` class composition:

.. graphviz::

   digraph architecture {
      node [shape=record fontname=Helvetica fontsize=10];
      rankdir=UD;
      
      InstrumentInterface [label="{InstrumentInterface|+ open()\l+ close()\l+ write(command: str)\l+ read(): str\l+ query(command: str): str\l}"];
      
      Instrument [label="{Instrument|+ identity()\l+ reset()\l+ status()\l}"];
      Oscilloscope [label="{Oscilloscope|+ run()\l+ stop()\l+ single()\l+ autoscale()\l}"];
      
      Acquire [label="{Acquire|+ sync()\l+ _mode: Mode\l+ _type: Type\l}"];
      Channel [label="{Channel|+ sync()\l+ coupling: Coupling\l+ display: DisplayState\l}"];
      Timebase [label="{Timebase|+ sync()\l+ mode: Mode\l+ position: float\l}"];
      Trigger [label="{Trigger|+ sync()\l+ mode: Mode\l+ level: float\l}"];
      Waveform [label="{Waveform|+ sync()\l+ format: Format\l+ source: Source\l}"];
      WaveGen [label="{WaveGen|+ sync()\l+ function: Function\l+ output: OutputState\l}"];
      
      InstrumentInterface -> Instrument [arrowhead="onormal", style="dashed"];
      Instrument -> Oscilloscope [arrowhead="onormal", style="dashed"];
      
      Oscilloscope -> Acquire [arrowhead="odiamond"];
      Oscilloscope -> Channel [arrowhead="odiamond"];
      Oscilloscope -> Timebase [arrowhead="odiamond"];
      Oscilloscope -> Trigger [arrowhead="odiamond"];
      Oscilloscope -> Waveform [arrowhead="odiamond"];
      Oscilloscope -> WaveGen [arrowhead="odiamond"];
      
      {rank=same; Acquire Channel Timebase Trigger Waveform WaveGen}
   }


Oscilloscope Core
-----------------

.. automodule:: pymetr.oscilloscope.core.Oscilloscope
   :members:
   :undoc-members:
   :show-inheritance:

Oscilloscope Subsystems
-----------------------

The subsystems are instantiated within the ``Oscilloscope`` class and are accessed through the corresponding attributes.
Each subsystem class focuses on a specific area of oscilloscope functionality, providing specialized methods and properties for that domain.

Acquire Subsystem
-----------------

.. automodule:: pymetr.oscilloscope.acquire
   :members:
   :undoc-members:
   :show-inheritance:

The ``Acquire`` subsystem manages data acquisition settings, offering control over how the oscilloscope captures and processes the signal data.

Channel Subsystem
-----------------

.. automodule:: pymetr.oscilloscope.channel
   :members:
   :undoc-members:
   :show-inheritance:

Each channel of the oscilloscope is represented by a ``Channel`` object, allowing individual control over display, scaling, and other channel-specific settings.

Timebase Subsystem
------------------

.. automodule:: pymetr.oscilloscope.timebase
   :members:
   :undoc-members:
   :show-inheritance:

The ``Timebase`` subsystem governs the horizontal sweep of the oscilloscope, dictating the scale and position of the waveform in time.

Trigger Subsystem
-----------------

.. automodule:: pymetr.oscilloscope.trigger
   :members:
   :undoc-members:
   :show-inheritance:

Trigger settings are crucial for accurate waveform capture. The ``Trigger`` subsystem provides precise control over when the oscilloscope starts acquiring data.

Waveform Subsystem
------------------

.. automodule:: pymetr.oscilloscope.waveform
   :members:
   :undoc-members:
   :show-inheritance:

After acquisition, the ``Waveform`` subsystem takes over, dealing with waveform data retrieval and analysis.

WaveGen Subsystem
-----------------

.. automodule:: pymetr.oscilloscope.wavegen
   :members:
   :undoc-members:
   :show-inheritance:

Some oscilloscopes come with a built-in waveform generator. The ``WaveGen`` subsystem manages this feature, controlling waveform output and modulation.


Root-Level Functions
====================

Beyond the subsystems, the ``Oscilloscope`` class includes root-level functions. These include functions like `run`, `stop`, `single`, and `autoscale`.

.. note:: The ``Oscilloscope`` class is designed with the user in mind, abstracting the complexities of the oscilloscope operation and providing a user-friendly interface that reflects the natural workflow of an engineer or technician working with the instrument.

Getting Started with the Oscilloscope Class
-------------------------------------------

To begin using the ``Oscilloscope`` class, first ensure that PyVISA is installed and properly configured in your environment. Here's a quick rundown on creating an instance of the ``Oscilloscope`` and running basic operations:

.. code-block:: python

   from pymetr.oscilloscope.core import Oscilloscope

   # Replace with your oscilloscope's VISA resource string
   resource_string = 'TCPIP0::192.168.1.111::hislip0::INSTR'
   osc = Oscilloscope(resource_string)
   osc.open()
   print(f"Identification string: '{osc.identity()}'")
   osc.close()

Extending the Oscilloscope Class
---------------------------------

Some specific models of osilloscopes may have subsystems or settings which differ from the Keysight DSOX1204G. That this class can be used as a base class to create specific models of oscilloscopes.

.. code-block:: python

   from pymetr.oscilloscope.core import Oscilloscope

   Class oscilloscope_XYZ(Oscilloscope):
      # Continue example code
