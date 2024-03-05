Subsystem Practical Coding Example
==================================

This section provides a concrete example of how to create a subsystem within the library, using the waveform subsystem of an oscilloscope as a case study. It highlights the use of properties with getters and setters to keep the software model and the physical instrument state synchronized.

Subsystem Synchronization
-------------------------

The library employs property decorators to define getters and setters for instrument parameters, facilitating the real-time synchronization of the software model with the instrument's actual settings. This synchronization ensures that changes to parameters within the software are immediately reflected in the instrument's configuration, allowing for robust error handling and prompt feedback.

**Getters and Setters:**

- **Getters**: Retrieve the current value of an instrument setting directly from the hardware, ensuring that the software's state is always up-to-date.
- **Setters**: Send updated values to the instrument whenever a property is assigned a new value, followed by querying the instrument to validate the change.

These mechanisms ensure that the instrument's object model within the software and its physical state remain aligned, providing a reliable and consistent interface for users.

Creating the Waveform Subsystem
-------------------------------

The waveform subsystem controls waveform settings on the oscilloscope. It demonstrates how to encapsulate SCPI commands for setting and querying waveform parameters, such as points, points mode, and format.

.. code-block:: python
   :caption: Waveform Subsystem Example
   :name: waveform-subsystem-example

   class WaveformSubsystem(InstrumentSubsystem):
       """A class to represent the waveform subsystem of an oscilloscope."""
       
       def __init__(self, parent):
           super().__init__(parent)
           self._points = None
           self._points_mode = None
           self._format = None

       @property
       def points(self):
           """Gets/sets the number of points in the waveform."""
           if self._points is None:
               self._points = int(self._parent.query(":WAVEFORM:POINTS?"))
           return self._points

       @points.setter
       def points(self, value):
           self._parent.write(f":WAVEFORM:POINTS {value}")
           self._points = value  # Synchronize the software model with the instrument

       @property
       def points_mode(self):
           """Gets/sets the points mode of the waveform."""
           if self._points_mode is None:
               self._points_mode = self._parent.query(":WAVEFORM:POINTS:MODE?")
           return self._points_mode

       @points_mode.setter
       def points_mode(self, value):
           self._parent.write(f":WAVEFORM:POINTS:MODE {value}")
           self._points_mode = value  # Synchronize the software model with the instrument

       @property
       def format(self):
           """Gets/sets the format of the waveform data."""
           if self._format is None:
               self._format = self._parent.query(":WAVEFORM:FORMAT?")
           return self._format

       @format.setter
       def format(self, value):
           self._parent.write(f":WAVEFORM:FORMAT {value}")
           self._format = value  # Synchronize the software model with the instrument

       def sync(self):
           """Synchronizes the subsystem with the current instrument settings."""
           self._points = None
           self._points_mode = None
           self._format = None
           # This forces the properties to re-query the instrument when next accessed

Using the Waveform Subsystem
----------------------------

With the waveform subsystem defined, users can interact with the oscilloscope's waveform settings intuitively:

.. code-block:: python
   :caption: Using the Waveform Subsystem
   :name: using-waveform-subsystem

   oscilloscope = Oscilloscope('GPIB::ADDRESS')
   oscilloscope.open()

   # Configure the waveform settings
   oscilloscope.waveform.points = 1200
   oscilloscope.waveform.points_mode = 'MAX'
   oscilloscope.waveform.format = 'ASC'

   # Retrieve and print the current waveform settings
   print(f"Waveform Points: {oscilloscope.waveform.points}")
   print(f"Waveform Points Mode: {oscilloscope.waveform.points_mode}")
   print(f"Waveform Format: {oscilloscope.waveform.format}")

This example demonstrates how to encapsulate the control and querying of instrument settings within a subsystem, providing a clear and straightforward interface for users. The use of property decorators for getters and setters not only simplifies the command structure but also ensures that the software model remains in sync with the physical state of the instrument, enhancing usability and reliability.
