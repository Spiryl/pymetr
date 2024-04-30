# --- trace_manager.py ---
import logging
logger = logging.getLogger(__name__)
import numpy as np
from PySide6.QtCore import QObject, Signal
from pymetr.core.trace import Trace

class TraceManager(QObject):
    traceDataChanged = Signal()
    traceAdded = Signal(Trace)
    traceRemoved = Signal(str)
    traceVisibilityChanged = Signal(str, bool)
    traceLabelChanged = Signal(str, str)
    traceColorChanged = Signal(str, str)
    traceModeChanged = Signal(str, str)
    traceLineThicknessChanged = Signal(str, float)
    traceLineStyleChanged = Signal(str, str)
    tracesCleared = Signal()

    def __init__(self):
        super().__init__()
        self.traces = []
        self.plot_mode = 'Single'
        self.trace_mode = 'Group'
        self.continuous_mode = False

        self.color_palette = ['#5E57FF', '#4BFF36', '#F23CA6', '#FF9535', '#02FEE4', '#2F46FA', '#FFFE13', '#55FC77']
        self.color_index = 0
        self.trace_counter = 0

    def add_trace(self, data):
        if self.plot_mode == "Single":
            self.clear_traces()
            self.trace_counter = 1  # Reset the trace counter

        if isinstance(data, Trace):
            logger.debug(f"Adding single trace: Label: {data.label}")
            self.process_trace(data)
        elif isinstance(data, (list, tuple)):
            for trace in data:
                if isinstance(trace, Trace):
                    logger.debug(f"Adding trace from list: Label: {trace.label}")
                    self.process_trace(trace)
                else:
                    logger.warning(f"Skipping non-Trace object: {trace}")
        else:
            logger.warning(f"Unsupported data type: {type(data)}")

        self.traceDataChanged.emit()

    def process_trace(self, trace):
        # Print out the attributes of the trace and their values
        logger.debug(f"Processing trace: Label: {trace.label}, Color: {trace.color}, Mode: {trace.mode}, "
                    f"Visible: {trace.visible}, Line Thickness: {trace.line_thickness}, Line Style: {trace.line_style}")

        if self.plot_mode == "Run":
            print(f"Plot mode is 'Run'")
            trace_labels = [t.label for t in self.traces]
            print(f"Existing trace labels: {trace_labels}")
            if trace.label in trace_labels:
                print(f"Trace with label '{trace.label}' already exists, updating it.")
                self.update_trace_by_label(trace)
                return
            else:
                print(f"Trace with label '{trace.label}' does not exist, adding it.")

        elif self.plot_mode == "Single":
            print(f"Plot mode is 'Single'")
            if trace.label:
                print(f"Trace label is '{trace.label}', keeping it as is.")
                trace.label = trace.label
            else:
                print(f"Trace label is empty, generating a new label: 'Trace_{self.trace_counter}'")
                trace.label = f"Trace_{self.trace_counter}"
                self.trace_counter += 1

        elif self.plot_mode == "Stack":
            print(f"Plot mode is 'Stack'")
            if trace.label:
                print(f"Trace label is '{trace.label}'")
                existing_labels = set(t.label for t in self.traces)
                print(f"Existing trace labels: {existing_labels}")
                if trace.label in existing_labels:
                    print(f"Trace label '{trace.label}' already exists, generating a unique label.")
                    trace.label = self.generate_unique_label(trace.label)
                else:
                    print(f"Trace label '{trace.label}' is unique, keeping it as is.")
            else:
                print("Trace label is empty, generating a new label.")
                trace.label = self.generate_unique_label()

        if not trace.color:
            print(f"Trace color is not set, assigning a color from the palette.")
            trace.color = self.get_next_color_from_palette()
        else:
            print(f"Trace color is '{trace.color}', keeping it as is.")

        print(f"Setting trace mode to '{self.trace_mode}'")
        trace.mode = self.trace_mode

        print(f"Appending trace to self.traces: {trace}")
        self.traces.append(trace)

        print(f"Emitting traceAdded signal with trace: {trace}")
        self.traceAdded.emit(trace)

    def generate_unique_label(self, base_label=None):
        existing_labels = set(trace.label for trace in self.traces if trace.label)

        if base_label:
            if base_label in existing_labels:
                counter = 1
                while True:
                    label = f"{base_label}_{counter}"
                    if label not in existing_labels:
                        return label
                    counter += 1
            else:
                return base_label
        else:
            label = f"Trace_{self.trace_counter}"
            self.trace_counter += 1
            return label

    def update_trace_by_label(self, trace):
        for index, existing_trace in enumerate(self.traces):
            if existing_trace.label == trace.label:
                self.traces[index] = trace
                break

    def set_plot_mode(self, mode):
        self.plot_mode = mode
        self.traceDataChanged.emit()

    def set_trace_mode(self, trace_mode):
        self.trace_mode = trace_mode
        for trace in self.traces:
            trace.mode = trace_mode
        self.traceDataChanged.emit()

    def get_next_color_from_palette(self):
        color = self.color_palette[self.color_index]
        self.color_index = (self.color_index + 1) % len(self.color_palette)
        return color

    def clear_traces(self):
        self.traces.clear()
        self.color_index = 0
        self.trace_counter = 1
        self.tracesCleared.emit()

    def on_plot_mode_changed(self, mode):
        self.plot_mode = mode

    def on_trace_mode_changed(self, mode):
        self.trace_mode = mode

    def emit_trace_data(self):
        self.traceDataChanged.emit()

    def group_all_traces(self):
        for trace in self.traces:
            trace.mode = "Group"
        self.emit_trace_data()

    def isolate_all_traces(self):
        for trace in self.traces:
            trace.mode = "Isolate"
        self.emit_trace_data()

    def add_random_trace(self):
        trace = TraceGenerator.generate_random_trace(self.trace_mode)
        self.add_trace(trace)

    def set_trace_visibility(self, trace_label, visible):
        for trace in self.traces:
            if trace.label == trace_label:
                logger.debug(f"TM: Setting visibility for trace '{trace_label}' to {visible}")
                trace.visible = visible
                self.traceVisibilityChanged.emit(trace_label, visible)
                break

    def set_trace_label(self, old_label, new_label):
        for trace in self.traces:
            if trace.label == old_label:
                logger.debug(f"TM: Updating label for trace '{old_label}' to '{new_label}'")
                trace.label = new_label
                self.traceLabelChanged.emit(old_label, new_label)
                break

    def set_trace_color(self, trace_label, color):
        for trace in self.traces:
            if trace.label == trace_label:
                logger.debug(f"TM: Setting color for trace '{trace_label}' to {color}")
                trace.color = color
                self.traceColorChanged.emit(trace_label, color)
                break

    def set_trace_mode(self, trace_label, mode):
        for trace in self.traces:
            if trace.label == trace_label:
                logger.debug(f"TM: Setting mode for trace '{trace_label}' to {mode}")
                trace.mode = mode
                self.traceModeChanged.emit(trace_label, mode)
                break

    def set_trace_line_thickness(self, trace_label, thickness):
        for trace in self.traces:
            if trace.label == trace_label:
                logger.debug(f"TM: Setting thickness for trace '{trace_label}' to {thickness}")
                trace.line_thickness = thickness
                self.traceLineThicknessChanged.emit(trace_label, thickness)
                break

    def set_trace_line_style(self, trace_label, style):
        for trace in self.traces:
            if trace.label == trace_label:
                logger.debug(f"TM: Setting line style for trace '{trace_label}' to {style}")
                trace.line_style = style
                self.traceLineStyleChanged.emit(trace_label, style)
                break

    def remove_trace(self, trace_label):
        for trace in self.traces:
            if trace.label == trace_label:
                self.traces.remove(trace)
                self.traceRemoved.emit(trace_label)

class TraceGenerator:

    @staticmethod
    def generate_random_trace(mode='Group'):
        x = np.arange(100)
        y = np.random.normal(loc=0, scale=20, size=100)
        trace = Trace(
            x_data=x,
            data=y,
            visible=True,
            line_thickness=1.0,
            line_style='Solid',
            mode=mode
        )
        return trace