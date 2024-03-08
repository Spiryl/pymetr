
PyMetr API
==========

Instrument Base Class API
-------------------------

.. autoclass:: pymetr.instrument.Instrument
   :members:
   :undoc-members:
   :show-inheritance:


Oscilloscope
-----------------

.. automodule:: pymetr.oscilloscope.Oscilloscope
   :members:
   :undoc-members:
   :show-inheritance:

Oscilloscope Subsystems
-----------------------

The subsystems are instantiated within the ``Oscilloscope`` class and are accessed through the corresponding attributes.
Each subsystem class focuses on a specific area of oscilloscope functionality, providing specialized methods and properties for that domain.

Acquire Subsystem
-----------------

.. automodule:: pymetr.subsystems.Acquire
   :members:
   :undoc-members:
   :show-inheritance:

The ``Acquire`` subsystem manages data acquisition settings, offering control over how the oscilloscope captures and processes the signal data.

Channel Subsystem
-----------------

.. automodule:: pymetr.subsystems.Channel
   :members:
   :undoc-members:
   :show-inheritance:

Each channel of the oscilloscope is represented by a ``Channel`` object, allowing individual control over display, scaling, and other channel-specific settings.

Timebase Subsystem
------------------

.. automodule:: pymetr.subsystems.Timebase
   :members:
   :undoc-members:
   :show-inheritance:

The ``Timebase`` subsystem governs the horizontal sweep of the oscilloscope, dictating the scale and position of the waveform in time.

Trigger Subsystem
-----------------

.. automodule:: pymetr.subsystems.Trigger
   :members:
   :undoc-members:
   :show-inheritance:

Trigger settings are crucial for accurate waveform capture. The ``Trigger`` subsystem provides precise control over when the oscilloscope starts acquiring data.

Waveform Subsystem
------------------

.. automodule:: pymetr.subsystems.Waveform
   :members:
   :undoc-members:
   :show-inheritance:

After acquisition, the ``Waveform`` subsystem takes over, dealing with waveform data retrieval and analysis.

WaveGen Subsystem
-----------------

.. automodule:: pymetr.subsystems.WaveGen
   :members:
   :undoc-members:
   :show-inheritance:

Some oscilloscopes come with a built-in waveform generator. The ``WaveGen`` subsystem manages this feature, controlling waveform output and modulation.
