# --- trace_plot.py ---
import logging
logger = logging.getLogger(__name__)
import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPainter, QPixmap, QGuiApplication, QColor
from pymetr.core.trace import Trace

class TracePlot(QWidget):
    finished_update = Signal(bool)

    def __init__(self, trace_manager, parent=None):
        super().__init__(parent)
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_item = self.plot_layout.addPlot(row=0, col=0)
        self.plot_layout.setBackground('#1E1E1E')  # Set the desired background color

        # Set the color and transparency of grid lines
        axis_color = '#888888'  
        self.plot_item.getAxis('left').setPen(pg.mkPen(color=axis_color))  
        self.plot_item.getAxis('bottom').setPen(pg.mkPen(color=axis_color))  
        self.plot_item.getAxis('left').setGrid(24)  
        self.plot_item.getAxis('bottom').setGrid(24)  

        # Set the color of plot labels and title
        label_color = '#888888'
        self.plot_item.setTitle("", color=label_color)
        self.plot_item.setLabel("bottom", "X Axis", color=label_color)
        self.plot_item.setLabel("left", "Y Axis", color=label_color)
        self.plot_item.getAxis('bottom').showLabel(False)
        self.plot_item.getAxis('left').showLabel(False)

        self.legend = pg.LegendItem(offset=(70, 70))
        self.legend.setParentItem(self.plot_item)
        legend_color = (80, 80, 80, 80)  # Middle gray with half transparency (RGBA)
        self.legend.setLabelTextColor(label_color)
        self.legend.setBrush(pg.mkBrush(legend_color))
        # self.legend.setPen(pg.mkPen(color=label_color))

        self.additional_axes = []
        self.additional_view_boxes = []
        self.trace_view_boxes = {}

        self.trace_manager = trace_manager
        self.trace_axes = {}
        self.traces = {}
        self.trace_curves = {}

        self.init_roi_plot()
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_layout)

        self.continuous_mode = False

        self.plot_item.scene().sigMouseClicked.connect(self.handleMouseClicked)
        self.plot_item.vb.sigResized.connect(self.update_view_boxes)

        self.trace_manager.traceDataChanged.connect(self.update_plot)
        self.trace_manager.traceVisibilityChanged.connect(self.update_trace_visibility)
        self.trace_manager.traceLabelChanged.connect(self.update_trace_label)
        self.trace_manager.traceColorChanged.connect(self.update_trace_color)
        self.trace_manager.traceLineThicknessChanged.connect(self.update_trace_line_thickness)
        self.trace_manager.traceLineStyleChanged.connect(self.update_trace_line_style)
        self.trace_manager.traceRemoved.connect(self.remove_trace)
        self.trace_manager.tracesCleared.connect(self.clear_traces)

    def set_continuous_mode(self, mode):
        logger.debug(f"trace_plot: setting continuous mode: {mode}")
        self.continuous_mode = mode

    # --- Main Plot Methods ----------------
    def update_plot(self, trace_data=None):
        if trace_data is None:
            trace_data = self.trace_manager.traces
            logger.debug(f"Using trace data from trace_manager: {trace_data}")
        else:
            logger.debug(f"Received trace data: {trace_data}")

        if self.continuous_mode:
            logger.debug("Updating plot in continuous mode")

            # Clear traces that are no longer present in trace_data
            traces_to_remove = [trace_label for trace_label in self.trace_curves if trace_label not in [trace.label for trace in trace_data]]
            logger.debug(f"Traces to remove: {traces_to_remove}")
            for trace_label in traces_to_remove:
                logger.debug(f"Removing trace: {trace_label}")
                self.remove_trace(trace_label)

            # In continuous mode, update trace data for existing traces or create new traces
            for trace in trace_data:
                if trace.label in self.trace_curves:
                    logger.debug(f"Updating existing trace: {trace.label}")
                    curve = self.trace_curves[trace.label]
                    curve.setData(trace.x_data, trace.data)
                else:
                    logger.debug(f"Adding new trace: {trace.label}")
                    self._add_trace_to_plot(trace)
        else:
            logger.debug("Updating plot in non-continuous mode")
            # Clear traces that are no longer present in trace_data
            traces_to_remove = [trace_label for trace_label in self.trace_curves if trace_label not in [trace.label for trace in trace_data]]
            logger.debug(f"Traces to remove: {traces_to_remove}")
            for trace_label in traces_to_remove:
                logger.debug(f"Removing trace: {trace_label}")
                self.remove_trace(trace_label)

            # Update existing traces and add new traces
            for trace in trace_data:
                if trace.label in self.trace_curves:
                    logger.debug(f"Updating existing trace: {trace.label}")
                    self._update_existing_trace(trace)
                else:
                    logger.debug(f"Adding new trace: {trace.label}")
                    self._add_trace_to_plot(trace)

        # Check if any traces are in isolated mode
        has_isolated_traces = any(trace.mode == 'Isolate' for trace in trace_data)
        logger.debug(f"Has isolated traces: {has_isolated_traces}")

        if has_isolated_traces:
            logger.debug("Updating view boxes")
            self.update_view_boxes()

            logger.debug("Restoring view ranges")
            self.restore_view_ranges(trace_data)

        # Check if the region plot is visible
        if self.roi_plot_item is not None and self.roi_plot_item.isVisible():
            logger.debug("Updating ROI plot")
            self.update_roi_plot(trace_data)
        else:
            logger.debug("ROI plot is not visible, skipping update")

        self.finished_update.emit(True)

    def _update_existing_trace(self, trace):
        logger.debug(f"Updating existing trace: {trace.label}")
        curve = self.trace_curves[trace.label]
        curve.setData(trace.x_data, trace.data)
        curve.setVisible(trace.visible)

        logger.debug(f"Updating trace properties:")
        logger.debug(f"- Color: {trace.color}")
        logger.debug(f"- Line thickness: {trace.line_thickness}")
        logger.debug(f"- Line style: {trace.line_style}")
        pen = pg.mkPen(color=trace.color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))
        curve.setPen(pen)

        logger.debug(f"Removing existing legend item for trace: {trace.label}")
        self.legend.removeItem(trace.label)

        logger.debug(f"Adding new legend item for trace: {trace.label}")
        self.legend.addItem(curve, trace.label)

        if trace.mode == "Isolate":
            if trace.label not in self.trace_view_boxes:
                logger.debug(f"Creating new view box and axis for trace: {trace.label}")
                axis = pg.AxisItem("right", pen=pen)
                self.plot_layout.addItem(axis, row=0, col=len(self.additional_axes) + 1)
                self.additional_axes.append(axis)

                view_box = pg.ViewBox()
                axis.linkToView(view_box)
                view_box.setXLink(self.plot_item.vb)
                self.plot_layout.scene().addItem(view_box)
                self.additional_view_boxes.append(view_box)

                self.trace_view_boxes[trace.label] = view_box
                self.trace_axes[trace.label] = axis

                logger.debug(f"Moving curve to the new view box for trace: {trace.label}")
                self.plot_item.removeItem(curve)
                view_box.addItem(curve)

                if trace.y_range is not None:
                    logger.debug(f"Setting y-range for trace: {trace.label}")
                    view_box.setRange(yRange=trace.y_range, padding=0)
                    view_box.enableAutoRange(axis='y', enable=False)
                else:
                    logger.debug(f"Setting y-range to view box range for trace: {trace.label}")
                    trace.y_range = view_box.viewRange()[1]

                logger.debug(f"Connecting view box range changed signal for trace: {trace.label}")
                view_box.sigRangeChanged.connect(lambda view_box, _: self.handle_view_box_range_changed(view_box, trace))
            else:
                logger.debug(f"Updating existing view box and axis for trace: {trace.label}")
                view_box = self.trace_view_boxes[trace.label]
                axis = self.trace_axes[trace.label]

                if trace.y_range is not None:
                    logger.debug(f"Setting y-range for trace: {trace.label}")
                    view_box.setRange(yRange=trace.y_range, padding=0)
                    view_box.enableAutoRange(axis='y', enable=False)
                else:
                    logger.debug(f"Setting y-range to view box range for trace: {trace.label}")
                    trace.y_range = view_box.viewRange()[1]
                    view_box.enableAutoRange(axis='y')
        else:
            if trace.label in self.trace_view_boxes:
                logger.debug(f"Removing trace from isolated view box: {trace.label}")
                view_box = self.trace_view_boxes[trace.label]
                axis = self.trace_axes[trace.label]

                view_box.removeItem(curve)
                self.plot_item.addItem(curve)

                self.plot_layout.removeItem(axis)
                self.additional_axes.remove(axis)
                axis.deleteLater()

                self.plot_layout.scene().removeItem(view_box)
                self.additional_view_boxes.remove(view_box)
                view_box.deleteLater()

                del self.trace_view_boxes[trace.label]
                del self.trace_axes[trace.label]

    def _add_trace_to_plot(self, trace):
        logger.debug(f"Adding trace to plot: {trace.label}")
        visible = trace.visible
        color = trace.color
        legend_alias = trace.label

        if trace.x_data is not None:
            x = trace.x_data
        else:
            logger.debug(f"Generating x-axis data for trace: {trace.label}")
            x = np.arange(len(trace.data))

        y = trace.data
        mode = trace.mode

        if visible:
            pen = pg.mkPen(color=color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))

            if mode == "Group":
                logger.debug(f"Adding trace to main plot: {trace.label}")
                curve = self.plot_item.plot(x, y, pen=pen, name=legend_alias)
                self.legend.addItem(curve, legend_alias)
                self.trace_curves[trace.label] = curve
            else:
                logger.debug(f"Adding trace to isolated view box: {trace.label}")
                if trace.label not in self.trace_view_boxes:
                    logger.debug(f"Creating new view box and axis for trace: {trace.label}")
                    axis = pg.AxisItem("right", pen=pen)
                    self.plot_layout.addItem(axis, row=0, col=len(self.additional_axes) + 1)
                    self.additional_axes.append(axis)

                    view_box = pg.ViewBox()
                    axis.linkToView(view_box)
                    view_box.setXLink(self.plot_item.vb)
                    self.plot_layout.scene().addItem(view_box)
                    self.additional_view_boxes.append(view_box)

                    self.trace_view_boxes[trace.label] = view_box
                    self.trace_axes[trace.label] = axis

                    if trace.y_range is not None:
                        logger.debug(f"Setting y-range for trace: {trace.label}")
                        view_box.setRange(yRange=trace.y_range, padding=0)
                        view_box.enableAutoRange(axis='y', enable=False)
                    else:
                        logger.debug(f"Setting y-range to view box range for trace: {trace.label}")
                        trace.y_range = view_box.viewRange()[1]

                    logger.debug(f"Connecting view box range changed signal for trace: {trace.label}")
                    view_box.sigRangeChanged.connect(lambda view_box, _: self.handle_view_box_range_changed(view_box, trace))
                else:
                    logger.debug(f"Using existing view box and axis for trace: {trace.label}")
                    view_box = self.trace_view_boxes[trace.label]
                    axis = self.trace_axes[trace.label]

                curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                view_box.addItem(curve)
                self.legend.addItem(curve, legend_alias)
                self.trace_curves[trace.label] = curve
        else:
            logger.debug(f"Trace is not visible, skipping addition: {trace.label}")

    def remove_trace(self, trace_label):
        if trace_label in self.trace_curves:
            curve = self.trace_curves[trace_label]
            if curve.getViewBox():
                curve.getViewBox().removeItem(curve)
            else:
                self.plot_item.removeItem(curve)

            self.legend.removeItem(trace_label)
            del self.trace_curves[trace_label]

            if trace_label in self.trace_view_boxes:
                view_box = self.trace_view_boxes[trace_label]
                axis = self.trace_axes[trace_label]

                self.plot_layout.removeItem(axis)
                axis.deleteLater()
                self.additional_axes.remove(axis)

                self.plot_layout.scene().removeItem(view_box)
                view_box.deleteLater()
                self.additional_view_boxes.remove(view_box)

                del self.trace_view_boxes[trace_label]
                del self.trace_axes[trace_label]

    def clear_traces(self):
        for curve in self.trace_curves.values():
            if curve.getViewBox():
                curve.getViewBox().removeItem(curve)
            else:
                self.plot_item.removeItem(curve)

        self.traces.clear()
        self.trace_curves.clear()
        self.legend.clear()
        self.update_roi_plot()
        self.clear_additional_axes()

    # --- Isolated Trace Methods ----------------
    def restore_view_ranges(self, trace_data):
        if self.plot_item.vb.viewRange()[0] is not None:
            self.plot_item.vb.setRange(xRange=self.plot_item.vb.viewRange()[0], yRange=self.plot_item.vb.viewRange()[1], padding=0)

        for trace in trace_data:
            if trace.mode == "Isolate":
                view_box = self.trace_view_boxes.get(trace.label)
                if view_box and trace.y_range is not None:
                    view_box.setRange(yRange=trace.y_range, padding=0)
                else:
                    if view_box is not None:
                        view_box.enableAutoRange(axis='y')

    def handle_view_box_range_changed(self, view_box, _):
        if isinstance(view_box, pg.ViewBox):
            _, y_range = view_box.viewRange()
            for trace in self.trace_manager.traces:
                if trace.label in self.trace_view_boxes and self.trace_view_boxes[trace.label] == view_box:
                    trace.y_range = y_range
                    break
        else:
            print(f"Unexpected view_box object: {view_box}")

    def clear_additional_axes(self):
        for axis in self.additional_axes:
            self.plot_layout.removeItem(axis)
            axis.deleteLater()
        for view_box in self.additional_view_boxes:
            self.plot_layout.scene().removeItem(view_box)
            view_box.deleteLater()
        self.additional_axes.clear()
        self.additional_view_boxes.clear()
        self.legend.clear()
        self.trace_view_boxes.clear()
        self.trace_axes.clear()

    def update_view_boxes(self):
        for view_box in self.additional_view_boxes:
            view_box.setGeometry(self.plot_item.vb.sceneBoundingRect())
            view_box.linkedViewChanged(self.plot_item.vb, view_box.XAxis)

        for trace_label, view_box in self.trace_view_boxes.items():
            trace = next((t for t in self.trace_manager.traces if t.label == trace_label), None)
            if trace and trace.mode == "Isolate":
                if trace.y_range:
                    view_box.setRange(yRange=trace.y_range, padding=0)
                else:
                    view_box.enableAutoRange(axis='y')

    # --- Region Plot Methods ----------------
    def init_roi_plot(self):
        self.roi_plot_item = self.plot_layout.addPlot(row=1, col=0)
        self.roi_plot_item.setMaximumHeight(100)
        self.roi_plot_item.hide()  # Start as hidden
        self.roi = pg.LinearRegionItem()
        self.roi.setZValue(10)
        self.roi_plot = self.roi_plot_item.vb  # Properly assign the viewbox of the ROI plot item
        self.roi_plot.addItem(self.roi)  # Add the LinearRegionItem to the correct viewbox
        self.roi.sigRegionChanged.connect(self.update_main_plot)
        self.plot_item.sigXRangeChanged.connect(self.on_main_plot_range_changed)

    def on_roi_plot_enabled(self, enabled):
        if self.roi_plot_item is not None:
            self.roi_plot_item.setVisible(enabled)  # Toggle visibility
            if enabled:
                self.update_roi_plot(self.trace_manager.traces)
                self.set_roi_region()  # Adjust the ROI to current range

    def update_roi_plot(self, traces):
        if self.roi_plot_item is None or not self.roi_plot_item.isVisible():
            return

        self.roi_plot_item.clear()

        if isinstance(traces, Trace):
            traces = [traces]

        for trace in traces:
            if trace.visible:
                x_data = trace.x_data if trace.x_data is not None else np.arange(len(trace.data))
                self.roi_plot_item.plot(x_data, trace.data, pen=pg.mkPen(trace.color, width=trace.line_thickness))

        self.autoscale_roi_plot()

    def set_roi_region(self):
        if self.roi is not None and self.plot_item is not None:
            current_range = self.plot_item.viewRange()[0]
            self.roi.setRegion(current_range)

    def autoscale_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot.enableAutoRange()

    def on_main_plot_range_changed(self, view_box, range_):
        if self.roi is not None:
            self.roi.setRegion(view_box.viewRange()[0])

    def clear_roi_plot(self):
        if self.roi_plot_item is not None:
            self.roi_plot_item.clear()

    def update_main_plot(self):
        if self.roi is not None:
            roi_region = self.roi.getRegion()
            self.plot_item.vb.setXRange(roi_region[0], roi_region[1], padding=0)

     # --- Plot Label Methods ----------------

    def set_title(self, title):
        # Set the title of the plot
        self.plot_item.setTitle(title)

    def set_title_visible(self, visible):
        # Set the visibility of the plot title
        if visible:
            self.plot_item.setTitle(self.plot_item.titleLabel.text)
        else:
            self.plot_item.setTitle("")

    def set_x_label(self, label):
        # Set the label for the x-axis
        self.plot_item.setLabel("bottom", label)

    def set_x_label_visible(self, visible):
        # Set the visibility of the x-axis label
        self.plot_item.getAxis('bottom').showLabel(visible)

    def set_x_grid(self, visible):
        # Set the visibility of the x-axis grid
        self.plot_item.showGrid(x=visible)

    def set_y_label(self, label):
        # Set the label for the y-axis
        self.plot_item.setLabel("left", label)

    def set_y_label_visible(self, visible):
        # Set the visibility of the y-axis label
        self.plot_item.getAxis('left').showLabel(visible)

    def set_y_grid(self, visible):
        # Set the visibility of the y-axis grid
        self.plot_item.showGrid(y=visible)

    # --- Trace Update Methods ---------------
    def update_trace_visibility(self, trace_label, visible):
        logger.debug(f"Updating visibility for trace '{trace_label}' to {visible}")
        if trace_label in self.trace_curves:
            self.trace_curves[trace_label].setVisible(visible)

    def update_trace_label(self, old_label, new_label):
        logger.debug(f"Updating label for trace '{old_label}' to {new_label}")
        if old_label in self.trace_curves:
            curve = self.trace_curves[old_label]
            curve.setName(new_label)
            self.legend.removeItem(old_label)
            self.legend.addItem(curve, new_label)
            self.trace_curves[new_label] = curve
            del self.trace_curves[old_label]

            # Update the QLineEdit in the TraceListItem
            for i in range(self.parent().trace_control_panel.trace_list.count()):
                list_item = self.parent().trace_control_panel.trace_list.item(i)
                item_widget = self.parent().trace_control_panel.trace_list.itemWidget(list_item)
                if item_widget.trace.label == old_label:
                    item_widget.label.setText(new_label)
                    break

    def update_trace_color(self, trace_label, color):
        logger.debug(f"Updating color for trace '{trace_label}' to {color}")
        if trace_label in self.trace_curves:
            pen = self.trace_curves[trace_label].opts['pen']
            pen.setColor(color)
            self.trace_curves[trace_label].setPen(pen)

    def update_trace_mode(self, trace_label, mode):
        self.update_plot() # This is a hack right now.

    def update_trace_line_thickness(self, trace_label, thickness):
        logger.debug(f"Updating thickness for trace '{trace_label}' to {thickness}")
        if trace_label in self.trace_curves:
            pen = self.trace_curves[trace_label].opts['pen']
            pen.setWidth(thickness)
            self.trace_curves[trace_label].setPen(pen)

    def update_trace_line_style(self, trace_label, style):
        logger.debug(f"Updating line style for trace '{trace_label}' to {style}")
        if trace_label in self.trace_curves:
            pen = self.trace_curves[trace_label].opts['pen']
            pen.setStyle(self.get_line_style(style))
            self.trace_curves[trace_label].setPen(pen)

    def remove_trace(self, trace_label):
        logger.debug(f"Removing trace '{trace_label}'")
        if trace_label in self.trace_curves:
            curve = self.trace_curves[trace_label]
            if curve.getViewBox():
                curve.getViewBox().removeItem(curve)
            else:
                self.plot_item.removeItem(curve)
            self.legend.removeItem(trace_label)
            del self.trace_curves[trace_label]
        self.update_roi_plot(self.traces)

    def clear_traces(self):
        # Clear all traces from the plot, legend, and additional axes
        for curve in self.trace_curves.values():
            if curve.getViewBox():
                curve.getViewBox().removeItem(curve)
            else:
                self.plot_item.removeItem(curve)
        self.traces.clear()
        self.trace_curves.clear()
        self.legend.clear()

        # Clear additional axes
        for axis in self.additional_axes:
            self.plot_layout.removeItem(axis)
            axis.deleteLater()
        self.additional_axes.clear()
        self.update_roi_plot(self.traces)

    # --- Misc Methods ----------------
    def handleMouseClicked(self, event):
        # Handle the mouse click event to autoscale the main plot and isolated view boxes
        if event.double():
            self.plot_item.autoRange()  # Autoscale the main plot
            for view_box in self.trace_view_boxes.values():
                view_box.autoRange()  # Autoscale each isolated view box

    def capture_screenshot(self):
        # Capture a screenshot of the plot and copy it to the clipboard
        pixmap = QPixmap(self.plot_layout.size())
        painter = QPainter(pixmap)
        self.plot_layout.render(painter)
        painter.end()
        QGuiApplication.clipboard().setPixmap(pixmap)

    def get_line_style(self, line_style):
        # Convert the line style string to the corresponding Qt line style enum
        if line_style == 'Solid':
            return Qt.SolidLine
        elif line_style == 'Dash':
            return Qt.DashLine
        elif line_style == 'Dot':
            return Qt.DotLine
        elif line_style == 'Dash-Dot':
            return Qt.DashDotLine
        else:
            return Qt.SolidLine
        
    def set_highlight_color(self, color):
        color_obj = QColor(color)  # Convert string to QColor object if necessary
        color_obj.setAlpha(50)     # Set transparency to 50, adjust as needed for desired transparency

        # Convert QColor to an RGBA tuple that pyqtgraph can use
        rgba = (color_obj.red(), color_obj.green(), color_obj.blue(), color_obj.alpha())

        # Assuming you have an attribute `roi` which is your LinearRegionItem
        if hasattr(self, 'roi'):
            self.roi.setBrush(pg.mkBrush(rgba))