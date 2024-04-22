import numpy as np
import pyqtgraph as pg
from PySide6.QtWidgets import QWidget, QVBoxLayout
<<<<<<< Updated upstream
from PySide6.QtCore import Qt

=======
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPainter, QPixmap, QGuiApplication
from PySide6.QtWidgets import QApplication
>>>>>>> Stashed changes
from pymetr.core import Trace

class TracePlot(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.plot_layout = pg.GraphicsLayoutWidget()
        self.plot_item = self.plot_layout.addPlot(row=0, col=0)
        self.plot_item.showGrid(x=True, y=True)

        self.plot_item.setTitle("Plot Title")
        self.plot_item.setLabel("bottom", "X Axis")
        self.plot_item.setLabel("left", "Y Axis")

        self.legend = pg.LegendItem(offset=(70, 30))
        self.legend.setParentItem(self.plot_item)

        self.additional_axes = []
        self.additional_view_boxes = []
        self.trace_view_boxes = {}
        self.trace_axes = {}
<<<<<<< Updated upstream
        self.traces = {}  # Storing Trace objects
        self.trace_curves = {}  # Storing PlotCurveItem references
=======
        self.traces = {}
        self.trace_curves = {}
        self.trace_data_updated = False
>>>>>>> Stashed changes

        self.init_roi_plot()
        layout = QVBoxLayout(self)
        layout.addWidget(self.plot_layout)

<<<<<<< Updated upstream
        # TODO: move this to new method connect_signals when we get more stuff. 
        self.plot_item.scene().sigMouseClicked.connect(self.handleMouseClicked)


    # --- Plot Label Methods ----------------
=======
        # self.update_timer = QTimer()
        # self.update_timer.timeout.connect(self.update_plot)
        # self.update_timer.start(0)  # Set the timer interval to 0 for maximum update speed

        self.plot_item.scene().sigMouseClicked.connect(self.handleMouseClicked)

     # --- Plot Label Methods ----------------

>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
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
                self.update_roi_plot(self.traces)  # Ensure this uses current traces
                self.set_roi_region()  # Adjust the ROI to current range
=======
    # --- Trace Update Methods ---------------
    def update_trace_data(self, trace_data):
        # Update the trace data for a single trace or a list of traces
        if isinstance(trace_data, list):
            for trace in trace_data:
                self._update_single_trace(trace)
        else:
            self._update_single_trace(trace_data)

    def _update_single_trace(self, trace):
        # Update the data for a single trace and its corresponding view
        if trace.label in self.trace_curves:
            self.trace_curves[trace.label].setData(trace.x_data, trace.data)
>>>>>>> Stashed changes

    def update_roi_plot(self, traces):
        if self.roi_plot_item is None or not self.roi_plot_item.isVisible():
            return

        self.roi_plot_item.clear()

<<<<<<< Updated upstream
        if isinstance(traces, Trace):
            traces = [traces]  # Convert single Trace object to a list

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
            self.plot_item.vb.setXRange(*self.roi.getRegion(), padding=0)

    def update_plot(self, trace_data):
        self.plot_item.clear()
        self.clear_additional_axes()

        # Add print statements to check the range before making any changes
        print(f"Main plot range before update: {self.plot_item.viewRange()}")

        for trace in trace_data:
            visible = trace.visible
            color = trace.color
            legend_alias = trace.label
            x = trace.x_data if trace.x_data is not None else np.arange(len(trace.data))
            y = trace.data
            mode = trace.mode

            if visible:
                pen = pg.mkPen(color=color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))

                if mode == "Group":
                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    self.plot_item.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.trace_curves[trace.label] = curve
                else:  # Isolate mode
                    if trace.label not in self.trace_view_boxes:
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
                            print(f"Y-range is not None: {trace}.{trace.y_range}")
                            view_box.setRange(yRange=trace.y_range)
                            view_box.enableAutoRange(axis='y', enable=False)
                        else:
                            trace.y_range = view_box.viewRange()[1]
                            print(f"Y-range is None, Setting: {trace}.{trace.y_range}")

                        # Connect the viewRangeChanged signal
                        view_box.sigRangeChanged.connect(lambda _, obj=view_box, t=trace: self.handle_view_box_range_changed(obj, t))
                    else:
                        view_box = self.trace_view_boxes[trace.label]
                        axis = self.trace_axes[trace.label]

                    curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                    view_box.addItem(curve)
                    self.legend.addItem(curve, legend_alias)
                    self.trace_curves[trace.label] = curve

        self.plot_item.vb.sigResized.connect(self.update_view_boxes)  # Connect the sigResized signal
        print(f"Main plot range before viewbox update: {self.plot_item.viewRange()}")
        self.update_view_boxes()  # Update the position and size of the view boxes initially
        print(f"Main plot range after viewbox update: {self.plot_item.viewRange()}")
        self.restore_view_ranges(trace_data)
        print(f"Main plot range after restore view ranges update: {self.plot_item.viewRange()}")
        self.update_roi_plot(trace_data)

=======
    def update_trace_visibility(self, trace_id, visible):
        # Update the visibility of a trace
        if trace_id in self.trace_curves:
            self.trace_curves[trace_id].setVisible(visible)

    def update_trace_color(self, trace_id, color):
        # Update the color of a trace
        if trace_id in self.trace_curves:
            pen = self.trace_curves[trace_id].opts['pen']
            pen.setColor(color)
            self.trace_curves[trace_id].setPen(pen)

    def update_trace_label(self, trace_id, label):
        # Update the label of a trace
        if trace_id in self.trace_curves:
            self.trace_curves[trace_id].setName(label)
            self.legend.renameItem(trace_id, label)

    def update_trace_line_thickness(self, trace_id, thickness):
        # Update the line thickness of a trace
        if trace_id in self.trace_curves:
            pen = self.trace_curves[trace_id].opts['pen']
            pen.setWidth(thickness)
            self.trace_curves[trace_id].setPen(pen)

    def update_trace_line_style(self, trace_id, style):
        # Update the line style of a trace
        if trace_id in self.trace_curves:
            pen = self.trace_curves[trace_id].opts['pen']
            pen.setStyle(self.get_line_style(style))
            self.trace_curves[trace_id].setPen(pen)

>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
    def on_trace_data_updated(self):
        self.trace_data_updated = True

    # --- Main Plot Methods ----------------
    def update_plot(self, trace_data=None):
        if trace_data is None:
            trace_data = self.trace_manager.traces

        # Clear traces that are no longer present in trace_data
        traces_to_remove = [trace_label for trace_label in self.trace_curves if trace_label not in [trace.label for trace in trace_data]]
        for trace_label in traces_to_remove:
            self.remove_trace(trace_label)

        # Update existing traces
        for trace in trace_data:
            if trace.label in self.trace_curves:
                self._update_existing_trace(trace)
            else:
                self._add_trace_to_plot(trace)

        self.plot_item.vb.sigResized.connect(self.update_view_boxes)
        self.update_view_boxes()
        self.restore_view_ranges(trace_data)
        self.update_roi_plot(trace_data)

    def _update_existing_trace(self, trace):
        curve = self.trace_curves[trace.label]
        curve.setData(trace.x_data, trace.data)
        curve.setVisible(trace.visible)

        pen = pg.mkPen(color=trace.color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))
        curve.setPen(pen)

        # Remove the existing legend item
        self.legend.removeItem(trace.label)

        # Add a new legend item with the updated label
        self.legend.addItem(curve, trace.label)

        if trace.mode == "Isolate":
            if trace.label not in self.trace_view_boxes:
                # Create a new view box and axis for the trace
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

                # Move the curve to the new view box
                self.plot_item.removeItem(curve)
                view_box.addItem(curve)

                if trace.y_range is not None:
                    view_box.setRange(yRange=trace.y_range, padding=0)
                    view_box.enableAutoRange(axis='y', enable=False)
                else:
                    trace.y_range = view_box.viewRange()[1]

                view_box.sigRangeChanged.connect(lambda view_box, _: self.handle_view_box_range_changed(view_box, trace))
            else:
                view_box = self.trace_view_boxes[trace.label]
                axis = self.trace_axes[trace.label]

                if trace.y_range is not None:
                    view_box.setRange(yRange=trace.y_range, padding=0)
                    view_box.enableAutoRange(axis='y', enable=False)
                else:
                    trace.y_range = view_box.viewRange()[1]
                    view_box.enableAutoRange(axis='y')
        else:
            # If the trace mode is changed back to "Group", remove it from the isolated view box
            if trace.label in self.trace_view_boxes:
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
        visible = trace.visible
        color = trace.color
        legend_alias = trace.label

        if trace.x_data is not None:
            x = trace.x_data
        else:
            x = np.arange(len(trace.data))

        y = trace.data
        mode = trace.mode

        if visible:
            pen = pg.mkPen(color=color, width=trace.line_thickness, style=self.get_line_style(trace.line_style))

            if mode == "Group":
                curve = self.plot_item.plot(x, y, pen=pen, name=legend_alias)
                self.legend.addItem(curve, legend_alias)
                self.trace_curves[trace.label] = curve
            else:
                # Isolate mode
                if trace.label not in self.trace_view_boxes:
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
                        view_box.setRange(yRange=trace.y_range, padding=0)
                        view_box.enableAutoRange(axis='y', enable=False)
                    else:
                        trace.y_range = view_box.viewRange()[1]

                    view_box.sigRangeChanged.connect(lambda view_box, _: self.handle_view_box_range_changed(view_box, trace))
                else:
                    view_box = self.trace_view_boxes[trace.label]
                    axis = self.trace_axes[trace.label]

                curve = pg.PlotCurveItem(x, y, pen=pen, name=legend_alias)
                view_box.addItem(curve)
                self.legend.addItem(curve, legend_alias)
                self.trace_curves[trace.label] = curve

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

        self.clear_additional_axes()

    # --- Isolated Trace Methods ----------------
>>>>>>> Stashed changes
    def restore_view_ranges(self, trace_data):
        if self.plot_item.vb.viewRange()[0] is not None:
            self.plot_item.vb.setRange(xRange=self.plot_item.vb.viewRange()[0], yRange=self.plot_item.vb.viewRange()[1], padding=0)

        for trace in trace_data:
            if trace.mode == "Isolate":
                view_box = self.trace_view_boxes.get(trace.label)
<<<<<<< Updated upstream
                if view_box:
                    if trace.y_range is not None:
                        view_box.setRange(yRange=trace.y_range, padding=0)
                    else:
=======
                if view_box and trace.y_range is not None:
                    view_box.setRange(yRange=trace.y_range, padding=0)
                else:
                    if view_box is not None:
>>>>>>> Stashed changes
                        view_box.enableAutoRange(axis='y')

    def get_line_style(self, line_style):
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

    def handle_view_box_range_changed(self, view_box, trace):
        if isinstance(view_box, pg.ViewBox):
<<<<<<< Updated upstream
            _, y_range = view_box.viewRange()[1]
            if isinstance(trace, Trace):
                trace.y_range = y_range
                print(f"Trace: {trace.label}, Y-Range: {y_range}")
            elif isinstance(trace, list):
                for t in trace:
                    t.y_range = y_range
                    print(f"Trace: {t.label}, Y-Range: {y_range}")
=======
            _, y_range = view_box.viewRange()
            for trace in self.trace_manager.traces:
                if trace.label in self.trace_view_boxes and self.trace_view_boxes[trace.label] == view_box:
                    trace.y_range = y_range
                    break
>>>>>>> Stashed changes
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

<<<<<<< Updated upstream
=======
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

    # --- Misc Methods ----------------
>>>>>>> Stashed changes
    def handleMouseClicked(self, event):
        # Handle the mouse click event to autoscale the main plot and isolated view boxes
        if event.double():
            self.plot_item.autoRange()  # Autoscale the main plot
            for view_box in self.trace_view_boxes.values():
<<<<<<< Updated upstream
                view_box.autoRange()  # Autoscale each isolated view box
=======
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
>>>>>>> Stashed changes
