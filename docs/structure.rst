PyMetr Project Structure
========================

The PyMetr project is organized into the following directory structure:

.. code-block:: text

    pymetr/
    │
    ├── core/
    │   ├── instrument.py
    │   ├── subsystem.py
    │   ├── trace.py
    │   ├── marker.py
    │   ├── cursor.py
    │   ├── measurement.py
    │   ├── calculation.py
    │   └── __init__.py
    │
    ├── widgets/
    │   ├── control_dock.py
    │   ├── trace_control_page.py
    │   ├── marker_control_page.py
    │   ├── cursor_control_page.py
    │   ├── measurement_control_page.py
    │   ├── calculation_control_page.py
    │   ├── instrument_panel.py
    │   ├── instrument_control_dock.py
    │   ├── instrument_control_panel.py
    │   ├── trace_plot.py
    │   ├── quick_panel.py
    │   └── __init__.py
    │
    ├── managers/
    │   ├── instrument_manager.py
    │   ├── trace_manager.py
    │   ├── marker_manager.py
    │   ├── cursor_manager.py
    │   ├── measurement_manager.py
    │   ├── calculation_manager.py
    │   └── __init__.py
    │
    ├── main_window.py
    └── __init__.py

Core
----

The ``core`` directory contains the fundamental classes that define the core functionality of the PyMetr application.

instrument.py
^^^^^^^^^^^^^

- ``Instrument`` class
    - Represents a generic instrument that can be connected to and controlled.
    - Provides methods for opening and closing the instrument connection.
    - Defines signals for trace data availability.

  Signals:
    - ``trace_data_ready(object)``: Emitted when new trace data is available from the instrument.

subsystem.py
^^^^^^^^^^^^

- ``Subsystem`` class
    - Represents a subsystem of an instrument, such as a channel or a waveform.
    - Provides methods for configuring and controlling the subsystem.

trace.py
^^^^^^^^

- ``Trace`` class
    - Represents a trace or waveform data acquired from an instrument.
    - Contains properties such as data, x-axis values, and display settings.

marker.py
^^^^^^^^^

- ``Marker`` class
    - Represents a marker or cursor on a trace plot.
    - Contains properties such as position, color, and visibility.

cursor.py
^^^^^^^^^

- ``Cursor`` class
    - Represents a cursor or measurement point on a trace plot.
    - Contains properties such as position, color, and visibility.

measurement.py
^^^^^^^^^^^^^^

- ``Measurement`` class
    - Represents a measurement performed on trace data.
    - Contains properties such as measurement type, parameters, and results.

calculation.py
^^^^^^^^^^^^^^

- ``Calculation`` class
    - Represents a calculation performed on trace data or measurements.
    - Contains properties such as calculation type, parameters, and results.

Widgets
-------

The ``widgets`` directory contains the user interface components of the PyMetr application.

control_dock.py
^^^^^^^^^^^^^^^

- ``ControlDock`` class
    - Represents a dockable widget that contains various control pages.
    - Provides a tab widget to switch between different control pages.

trace_control_page.py
^^^^^^^^^^^^^^^^^^^^^

- ``TraceControlPage`` class
    - Represents a page in the control dock for managing trace settings.
    - Provides a list view of available traces and their properties.

  Signals:
    - ``trace_visibility_changed(str, bool)``: Emitted when the visibility of a trace is changed.
    - ``trace_color_changed(str, str)``: Emitted when the color of a trace is changed.
    - ``trace_mode_changed(str, str)``: Emitted when the mode of a trace is changed.
    - ``trace_line_width_changed(str, float)``: Emitted when the line width of a trace is changed.
    - ``trace_line_style_changed(str, str)``: Emitted when the line style of a trace is changed.
    - ``trace_deleted(str)``: Emitted when a trace is deleted.

- ``TraceListItem`` class
    - Represents an item in the trace list view.
    - Contains widgets for displaying and editing trace properties.

marker_control_page.py
^^^^^^^^^^^^^^^^^^^^^^

- ``MarkerControlPage`` class
    - Represents a page in the control dock for managing marker settings.
    - Provides a list view of available markers and their properties.

  Signals:
    - ``marker_added(Marker)``: Emitted when a new marker is added.
    - ``marker_updated(Marker)``: Emitted when the properties of a marker are updated.
    - ``marker_removed(str)``: Emitted when a marker is removed.

cursor_control_page.py
^^^^^^^^^^^^^^^^^^^^^^

- ``CursorControlPage`` class
    - Represents a page in the control dock for managing cursor settings.
    - Provides a list view of available cursors and their properties.

  Signals:
    - ``cursor_added(Cursor)``: Emitted when a new cursor is added.
    - ``cursor_updated(Cursor)``: Emitted when the properties of a cursor are updated.
    - ``cursor_removed(str)``: Emitted when a cursor is removed.

measurement_control_page.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``MeasurementControlPage`` class
    - Represents a page in the control dock for managing measurement settings.
    - Provides a list view of available measurements and their properties.

  Signals:
    - ``measurement_added(Measurement)``: Emitted when a new measurement is added.
    - ``measurement_updated(Measurement)``: Emitted when the properties of a measurement are updated.
    - ``measurement_removed(str)``: Emitted when a measurement is removed.

calculation_control_page.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``CalculationControlPage`` class
    - Represents a page in the control dock for managing calculation settings.
    - Provides a list view of available calculations and their properties.

  Signals:
    - ``calculation_added(Calculation)``: Emitted when a new calculation is added.
    - ``calculation_updated(Calculation)``: Emitted when the properties of a calculation are updated.
    - ``calculation_removed(str)``: Emitted when a calculation is removed.

instrument_panel.py
^^^^^^^^^^^^^^^^^^^

- ``InstrumentPanel`` class
    - Represents a panel for searching, selecting, connecting to, and disconnecting from instruments.
    - Provides a user interface for managing instrument connections.

  Signals:
    - ``instrument_selected(str)``: Emitted when an instrument is selected.
    - ``instrument_connected(str)``: Emitted when an instrument is connected.
    - ``instrument_disconnected(str)``: Emitted when an instrument is disconnected.

instrument_control_dock.py
^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``InstrumentControlDock`` class
    - Represents a dockable widget that contains instrument control panels.
    - Provides a tab widget to switch between different instrument control panels.

  Signals:
    - ``instrument_tab_changed(str)``: Emitted when the active instrument tab is changed.

instrument_control_panel.py
^^^^^^^^^^^^^^^^^^^^^^^^^^^

- ``InstrumentControlPanel`` class
    - Represents a control panel for a specific instrument.
    - Provides widgets for controlling instrument settings and acquiring data.

  Signals:
    - ``trace_data_ready(object)``: Emitted when new trace data is available from the instrument.
    - ``settings_changed(dict)``: Emitted when instrument settings are changed.

trace_plot.py
^^^^^^^^^^^^^

- ``TracePlot`` class
    - Represents a plot widget for displaying trace data.
    - Provides methods for adding, removing, and updating traces.

quick_panel.py
^^^^^^^^^^^^^^

- ``QuickPanel`` class
    - Represents a panel with quick access buttons for common actions.
    - Provides buttons for selecting plot mode, trace mode, and other frequently used functions.

  Signals:
    - ``plot_mode_changed(str)``: Emitted when the plot mode is changed.
    - ``trace_mode_changed(str)``: Emitted when the trace mode is changed.
    - ``roi_plot_toggled(bool)``: Emitted when the ROI plot is toggled.
    - ``group_all_clicked()``: Emitted when the "Group All" button is clicked.
    - ``isolate_all_clicked()``: Emitted when the "Isolate All" button is clicked.
    - ``test_trace_clicked()``: Emitted when the "Test Trace" button is clicked.
    - ``clear_traces_clicked()``: Emitted when the "Clear Traces" button is clicked.
    - ``add_instrument_clicked()``: Emitted when the "Add Instrument" button is clicked.
    - ``screenshot_clicked()``: Emitted when the "Screenshot" button is clicked.

Managers
--------

The ``managers`` directory contains classes responsible for managing the application's data and coordinating between the core classes and the user interface.

instrument_manager.py
^^^^^^^^^^^^^^^^^^^^^

- ``InstrumentManager`` class
    - Manages the connected instruments.
    - Handles instrument connection and disconnection.
    - Maintains a dictionary of connected instruments.

  Signals:
    - ``instrument_connected(str)``: Emitted when an instrument is connected.
    - ``instrument_disconnected(str)``: Emitted when an instrument is disconnected.

trace_manager.py
^^^^^^^^^^^^^^^^

- ``TraceManager`` class
    - Manages the traces displayed in the application.
    - Handles adding, removing, and updating traces.
    - Maintains a list of traces.

  Signals:
    - ``trace_added(Trace)``: Emitted when a new trace is added.
    - ``trace_visibility_changed(str, bool)``: Emitted when the visibility of a trace is changed.
    - ``trace_color_changed(str, str)``: Emitted when the color of a trace is changed.
    - ``trace_label_changed(str, str)``: Emitted when the label of a trace is changed.
    - ``trace_line_thickness_changed(str, float)``: Emitted when the line thickness of a trace is changed.
    - ``trace_line_style_changed(str, str)``: Emitted when the line style of a trace is changed.
    - ``trace_removed(str)``: Emitted when a trace is removed.

marker_manager.py
^^^^^^^^^^^^^^^^^

- ``MarkerManager`` class
    - Manages the markers displayed in the application.
    - Handles adding, removing, and updating markers.
    - Maintains a list of markers.

  Signals:
    - ``marker_added(Marker)``: Emitted when a new marker is added.
    - ``marker_updated(Marker)``: Emitted when the properties of a marker are updated.
    - ``marker_removed(str)``: Emitted when a marker is removed.

cursor_manager.py
^^^^^^^^^^^^^^^^^

- ``CursorManager`` class
    - Manages the cursors displayed in the application.
    - Handles adding, removing, and updating cursors.
    - Maintains a list of cursors.

  Signals:
    - ``cursor_added(Cursor)``: Emitted when a new cursor is added.
    - ``cursor_updated(Cursor)``: Emitted when the properties of a cursor are updated.
    - ``cursor_removed(str)``: Emitted when a cursor is removed.

measurement_manager.py
^^^^^^^^^^^^^^^^^^^^^^

- ``MeasurementManager`` class
    - Manages the measurements performed in the application.
    - Handles adding, removing, and updating measurements.
    - Maintains a list of measurements.

  Signals:
    - ``measurement_added(Measurement)``: Emitted when a new measurement is added.
    - ``measurement_updated(Measurement)``: Emitted when the properties of a measurement are updated.
    - ``measurement_removed(str)``: Emitted when a measurement is removed.

calculation_manager.py
^^^^^^^^^^^^^^^^^^^^^^

- ``CalculationManager`` class
    - Manages the calculations performed in the application.
    - Handles adding, removing, and updating calculations.
    - Maintains a list of calculations.

  Signals:
    - ``calculation_added(Calculation)``: Emitted when a new calculation is added.
    - ``calculation_updated(Calculation)``: Emitted when the properties of a calculation are updated.
    - ``calculation_removed(str)``: Emitted when a calculation is removed.

main_window.py
--------------

- ``MainWindow`` class
    - Represents the main window of the PyMetr application.
    - Initializes and lays out the main user interface components.
    - Handles the signal-slot connections between different components.