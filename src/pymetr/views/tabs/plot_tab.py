# pymetr/views/tabs/plot_tab.py
from typing import Optional, Any
from PySide6.QtWidgets import (
    QVBoxLayout, QSplitter, QWidget,
    QLabel, QSizePolicy
)
from PySide6.QtCore import Qt, Slot, QTimer
from PySide6.QtGui import QAction
import pyqtgraph as pg
import numpy as np

from pymetr.views.tabs.base import BaseTab
from pymetr.views.widgets.plot_view import PlotView
from pymetr.core.logging import logger

class PlotTab(BaseTab):
    """Full-featured plot tab with ROI and toolbar."""
    
    def __init__(self, state, model_id: str, parent=None):
        logger.debug(f"Initializing PlotTab for model_id: {model_id}")
        # Initialize member variables
        self.plot_view: Optional[PlotView] = None
        self.roi_plot_area: Optional[pg.PlotWidget] = None
        self.roi_plot_item: Optional[pg.PlotItem] = None
        self.roi: Optional[pg.LinearRegionItem] = None
        
        # ROI update handling
        self._roi_update_needed = False
        self._suppress_roi_updates = False
        self.roi_update_timer = QTimer()
        self.roi_update_timer.setSingleShot(True)
        self.roi_update_timer.timeout.connect(self._apply_roi_update)
        
        # Call base class init
        super().__init__(state, model_id, parent)
        logger.debug("PlotTab initialization complete")
    
    def _setup_ui(self):
        """Initialize the tab UI components."""
        logger.debug("Setting up UI for PlotTab")
        try:
            # Create a layout for the content widget (same pattern as ScriptTab)
            layout = QVBoxLayout(self.content_widget)
            layout.setContentsMargins(0, 0, 0, 0)
            layout.setSpacing(0)
            logger.debug("Content widget layout created for PlotTab")
            
            # Create main plot view
            logger.debug("Creating main PlotView")
            self.plot_view = PlotView(self.state, self._model_id, self)
            layout.addWidget(self.plot_view)
            logger.debug("Main PlotView added to layout")
            
            # Create a container for the ROI plot area
            logger.debug("Creating ROI container widget")
            roi_container = QWidget()
            roi_layout = QVBoxLayout(roi_container)
            roi_layout.setContentsMargins(0, 0, 0, 0)
            roi_layout.setSpacing(0)
            
            # Setup ROI plot area and add it to the container
            logger.debug("Setting up ROI plot area")
            self._setup_roi_plot()
            roi_layout.addWidget(self.roi_plot_area)
            logger.debug("ROI plot area added to ROI container")
            
            # Add the ROI container to the main layout
            layout.addWidget(roi_container)
            logger.debug("ROI container added to main layout")
            
            # Setup toolbar actions
            logger.debug("Setting up toolbar for PlotTab")
            self._setup_toolbar()
            
            # Connect plot signals
            if hasattr(self.plot_view, 'plot_item'):
                logger.debug("Connecting plot range-changed signal")
                self.plot_view.plot_item.sigRangeChanged.connect(
                    self._handle_main_plot_range_changed
                )
            else:
                logger.warning("PlotView has no attribute 'plot_item'")
        except Exception as e:
            logger.error(f"Error during PlotTab UI setup: {e}")

    def _setup_toolbar(self):
        """Setup toolbar actions."""
        logger.debug("Setting up toolbar actions for PlotTab")
        try:
            # View menu
            view_menu = self.toolbar.addDropdown("View")
            logger.debug("Added 'View' dropdown to toolbar")
            
            # ROI visibility toggle
            self.show_roi_action = QAction("Show ROI", view_menu)
            self.show_roi_action.setCheckable(True)
            self.show_roi_action.setChecked(True)
            self.show_roi_action.triggered.connect(self._handle_roi_visibility)
            view_menu.addAction(self.show_roi_action)
            logger.debug("ROI visibility toggle added to toolbar")
            
            view_menu.addSeparator()
            
            # Auto range action
            auto_range_action = QAction("Auto Range", view_menu)
            auto_range_action.triggered.connect(self._handle_auto_range)
            view_menu.addAction(auto_range_action)
            logger.debug("Auto Range action added to toolbar")
            
            self.toolbar.addSeparator()
            self.toolbar.addStretch()
            logger.debug("Toolbar setup for PlotTab complete")
        except Exception as e:
            logger.error(f"Error setting up toolbar in PlotTab: {e}")

    def _setup_roi_plot(self):
        """Setup the ROI plot area."""
        logger.debug("Setting up ROI plot area in PlotTab")
        try:
            self.roi_plot_area = pg.PlotWidget()
            self.roi_plot_area.setMinimumHeight(60)
            self.roi_plot_area.setMaximumHeight(60)
            self.roi_plot_area.setSizePolicy(
                QSizePolicy.Expanding, 
                QSizePolicy.Fixed
            )
            self.roi_plot_area.setBackground('#2A2A2A')
            logger.debug("ROI plot area widget created")
            
            self.roi_plot_item = self.roi_plot_area.getPlotItem()
            self.roi_plot_item.showGrid(x=True, y=False)
            self.roi_plot_item.getAxis('left').hide()
            self.roi_plot_item.setMouseEnabled(x=False, y=False)
            logger.debug("ROI plot item configured (grid, axis, mouse settings)")
            
            # Style the bottom axis
            bottom_axis = self.roi_plot_item.getAxis('bottom')
            bottom_axis.setPen(pg.mkPen('w'))
            bottom_axis.setTextPen(pg.mkPen('w'))
            logger.debug("Bottom axis styling applied in ROI plot")
            
            # Add ROI selector
            self.roi = pg.LinearRegionItem()
            self.roi_plot_item.addItem(self.roi)
            self.roi.sigRegionChanged.connect(self._handle_roi_changed)
            logger.debug("ROI selector added and connected")
        except Exception as e:
            logger.error(f"Error in _setup_roi_plot: {e}")

    def _handle_roi_visibility(self, visible: bool):
        """Handle ROI visibility toggle."""
        logger.debug(f"ROI visibility toggle triggered: {visible}")
        try:
            self.roi_plot_area.setVisible(visible)
            if self.model:
                self.model.set_property('roi_visible', visible)
                logger.debug(f"Model property 'roi_visible' set to {visible}")
        except Exception as e:
            logger.error(f"Error in _handle_roi_visibility: {e}")

    def _handle_auto_range(self):
        """Handle auto range action."""
        logger.debug("Auto range action triggered")
        try:
            if self.plot_view:
                self._suppress_roi_updates = True
                self.plot_view.autoRange()
                self._suppress_roi_updates = False
                logger.debug("Auto range applied successfully")
            else:
                logger.error("PlotView not available in _handle_auto_range")
        except Exception as e:
            logger.error(f"Error in _handle_auto_range: {e}")

    def _handle_roi_changed(self):
        """Handle ROI region changes."""
        # logger.debug("ROI region changed")
        try:
            if not self.model or self._suppress_roi_updates:
                logger.debug("Either no model or ROI updates suppressed; returning")
                return
            region = self.roi.getRegion()
            region_list = [float(x) for x in region]
            # logger.debug(f"ROI region: {region_list}")
            
            if region_list != self.model.get_property('roi'):
                logger.debug("New ROI region differs from model property; updating model")
                self.model.set_property('roi', region_list)
                self._suppress_roi_updates = True
                if hasattr(self.plot_view, 'plot_item'):
                    self.plot_view.plot_item.setXRange(*region, padding=0)
                    logger.debug("PlotView X range updated to ROI region")
                else:
                    logger.warning("PlotView has no attribute 'plot_item'")
                self._suppress_roi_updates = False
        except Exception as e:
            logger.error(f"Error in _handle_roi_changed: {e}")

    @Slot(object, object)
    def _handle_main_plot_range_changed(self, viewbox, ranges):
        """Update ROI when main plot range changes."""
        logger.debug(f"Main plot range changed: {ranges}")
        try:
            if self._suppress_roi_updates:
                logger.debug("ROI updates are suppressed; skipping _handle_main_plot_range_changed")
                return
            if self.roi:
                self.roi.setRegion(ranges[0])
                logger.debug(f"ROI region set to: {ranges[0]}")
            # Queue ROI plot update
            self._roi_update_needed = True
            self.roi_update_timer.start(100)
            logger.debug("ROI update timer started")
        except Exception as e:
            logger.error(f"Error in _handle_main_plot_range_changed: {e}")

    def _apply_roi_update(self):
        """Apply queued ROI updates."""
        logger.debug("Applying ROI update")
        try:
            if not self._roi_update_needed or not self.plot_view:
                logger.debug("No ROI update needed or PlotView unavailable")
                return
            
            self.roi_plot_area.clear()
            logger.debug("Cleared ROI plot area")
            
            if not self.model:
                logger.error("No model found in _apply_roi_update; aborting update")
                return
            
            # Calculate full data range efficiently
            x_ranges = []
            for trace_id, curve in self.plot_view.traces.items():
                if curve.isVisible():
                    data = curve.getData()
                    if data[0].size > 0:
                        rmin = np.nanmin(data[0])
                        rmax = np.nanmax(data[0])
                        x_ranges.append((rmin, rmax))
                        logger.debug(f"Trace {trace_id}: x-range = ({rmin}, {rmax})")
            
            if x_ranges:
                x_min = min(r[0] for r in x_ranges)
                x_max = max(r[1] for r in x_ranges)
                if np.isfinite(x_min) and np.isfinite(x_max):
                    padding = (x_max - x_min) * 0.05
                    self.roi_plot_item.setXRange(x_min - padding, x_max + padding, padding=0)
                    logger.debug(f"ROI plot X range set to ({x_min - padding}, {x_max + padding})")
            
            # Add visible traces to ROI plot efficiently
            for trace_id, curve in self.plot_view.traces.items():
                if curve.isVisible():
                    data = curve.getData()
                    self.roi_plot_area.plot(data[0], data[1], pen=curve.opts['pen'])
                    logger.debug(f"Plotted trace {trace_id} on ROI plot")
            
            # Re-add ROI
            self.roi_plot_area.addItem(self.roi)
            self._roi_update_needed = False
            logger.debug("ROI update applied successfully")
        except Exception as e:
            logger.error(f"Error in _apply_roi_update: {e}")

    def set_model(self, model_id: str):
        """Set up model and manage ROI state."""
        logger.debug(f"PlotTab set_model called for model_id: {model_id}")
        try:
            super().set_model(model_id)
            if self.model:
                # Set initial ROI state
                roi = self.model.get_property("roi", None)
                if roi and len(roi) == 2 and self.roi:
                    self.roi.setRegion(roi)
                    logger.debug(f"Initial ROI state set to {roi}")
                else:
                    logger.debug("No initial ROI state available")
                
                # Set ROI visibility
                roi_visible = self.model.get_property("roi_visible", True)
                self.roi_plot_area.setVisible(roi_visible)
                self.show_roi_action.setChecked(roi_visible)
                logger.debug(f"ROI visibility set to {roi_visible}")
                
                # Initial ROI plot update
                self._roi_update_needed = True
                self.roi_update_timer.start(100)
                logger.debug("ROI update timer started for initial update")
            else:
                logger.error("No model found in set_model for PlotTab")
        except Exception as e:
            logger.error(f"Error in set_model of PlotTab: {e}")
