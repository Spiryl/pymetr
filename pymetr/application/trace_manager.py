# --- trace_manager.py ---
import logging
logger = logging.getLogger()
import numpy as np
from PySide6.QtCore import QObject, Signal
from PySide6.QtWidgets import QApplication
from pymetr.core import Trace

class TraceManager(QObject):
    traceDataChanged = Signal()
    traceDataUpdated = Signal()
    traceAdded = Signal(Trace)
    traceVisibilityChanged = Signal(str, bool)
    traceColorChanged = Signal(str, str)
    traceLabelChanged = Signal(str, str)
    traceLineThicknessChanged = Signal(str, float)
    traceLineStyleChanged = Signal(str, str)
    traceRemoved = Signal(str)

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
            self.process_trace(data)
        elif isinstance(data, (list, tuple)):
            for trace in data:
                if isinstance(trace, Trace):
                    self.process_trace(trace)
                else:
                    logger.warning(f"Skipping non-Trace object: {trace}")
        else:
            logger.warning(f"Unsupported data type: {type(data)}")

        self.traceDataChanged.emit()
        self.traceDataUpdated.emit()

    def process_trace(self, trace):
        if self.plot_mode == "Single":
            if trace.label:
                trace.label = trace.label
            else:
                trace.label = f"Trace_{self.trace_counter}"
                self.trace_counter += 1
        elif self.plot_mode == "Stack":
            if trace.label:
                existing_labels = set(t.label for t in self.traces)
                if trace.label in existing_labels:
                    trace.label = self.generate_unique_label(trace.label)
            else:
                trace.label = self.generate_unique_label()
        elif self.plot_mode == "Run":
            if trace.label in [t.label for t in self.traces]:
                self.update_trace_by_label(trace)
                return

        if not trace.color:
            trace.color = self.get_next_color_from_palette()

        trace.mode = self.trace_mode
        self.traces.append(trace)
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
        self.traceDataUpdated.emit()
        
    def _update_single_trace(self, trace_data):
        for trace in self.traces:
            if trace.label == trace_data.label:

                if not np.array_equal(trace.data, trace_data.data):
                    trace.data = trace_data.data
                    trace.x_data = trace_data.x_data  # Update x_data
                if trace.color != trace_data.color:
                    trace.color = trace_data.color
                    self.traceColorChanged.emit(trace.label, trace.color)
                if trace.line_thickness != trace_data.line_thickness:
                    trace.line_thickness = trace_data.line_thickness
                    self.traceLineThicknessChanged.emit(trace.label, trace.line_thickness)
                if trace.line_style != trace_data.line_style:
                    trace.line_style = trace_data.line_style
                    self.traceLineStyleChanged.emit(trace.label, trace.line_style)
                self.traceDataChanged.emit()
                break
            else:
                if not trace_data.label:
                    trace_data.label = self.generate_unique_label()
                self.traces.append(trace_data)
                self.traceAdded.emit(trace_data)

    def set_plot_mode(self, mode):
        self.plot_mode = mode
        if mode == 'Single':
            self.clear_traces()
        self.traceDataChanged.emit()

    def set_trace_mode(self, trace_mode):
        self.trace_mode = trace_mode
        for trace in self.traces:
            trace.mode = trace_mode
        self.traceDataChanged.emit()

    def update_trace_data(self, trace_data):
        if isinstance(trace_data, list):
            for trace in trace_data:
                self._update_single_trace(trace)
        else:
            self._update_single_trace(trace_data)

    def get_next_color_from_palette(self):
        color = self.color_palette[self.color_index]
        self.color_index = (self.color_index + 1) % len(self.color_palette)
        return color

    def clear_traces(self):
        self.traces.clear()
        self.color_index = 0
        self.trace_counter = 1
        self.emit_trace_data()

    def remove_trace(self, trace):
        if trace in self.traces:
            self.traces.remove(trace)
            self.emit_trace_data()

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


class TraceGenerator:

    @staticmethod
    def generate_random_trace(mode='Group'):
        x = np.arange(100)-50
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
