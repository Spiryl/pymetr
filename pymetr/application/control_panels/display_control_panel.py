# --- display_control_panel.py ---
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QCheckBox, QLineEdit, QLabel, QDoubleSpinBox
from PySide6.QtCore import Signal

class DisplayControlPanel(QWidget):
    gridToggled = Signal(bool)
    xLogScaleToggled = Signal(bool)
    yLogScaleToggled = Signal(bool)
    xGridChanged = Signal(bool)
    yGridChanged = Signal(bool)
    titleChanged = Signal(str)
    titleVisibilityChanged = Signal(bool)
    xLabelChanged = Signal(str)
    xLabelVisibilityChanged = Signal(bool)
    yLabelChanged = Signal(str)
    yLabelVisibilityChanged = Signal(bool)

    def __init__(self, trace_plot, parent=None):
        super().__init__(parent)
        self.trace_plot = trace_plot
        self.layout = QHBoxLayout(self)

        # X-Axis Group Box
        self.x_axis_group_box = QGroupBox("X-Axis")
        x_axis_layout = QVBoxLayout()

        self.x_grid_checkbox = QCheckBox("X Grid")
        self.x_grid_checkbox.setChecked(True)
        self.x_grid_checkbox.stateChanged.connect(lambda state: self.xGridChanged.emit(state == 2))
        x_axis_layout.addWidget(self.x_grid_checkbox)

        self.x_log_scale_checkbox = QCheckBox("X Log Scale")
        self.x_log_scale_checkbox.stateChanged.connect(lambda state: self.xLogScaleToggled.emit(state == 2))
        x_axis_layout.addWidget(self.x_log_scale_checkbox)

        x_label_layout = QHBoxLayout()
        self.x_label_label = QLabel("X Label:")
        self.x_label_text_edit = QLineEdit("X")
        self.x_label_text_edit.textChanged.connect(self.xLabelChanged.emit)
        self.x_label_visibility_checkbox = QCheckBox("Show X Label")
        self.x_label_visibility_checkbox.setChecked(False)
        self.x_label_visibility_checkbox.stateChanged.connect(lambda state: self.xLabelVisibilityChanged.emit(state == 2))
        x_label_layout.addWidget(self.x_label_label)
        x_label_layout.addWidget(self.x_label_text_edit)
        x_label_layout.addWidget(self.x_label_visibility_checkbox)
        x_axis_layout.addLayout(x_label_layout)

        x_units_layout = QHBoxLayout()
        self.x_units_label = QLabel("X Units:")
        self.x_units_text_edit = QLineEdit("Units")
        x_units_layout.addWidget(self.x_units_label)
        x_units_layout.addWidget(self.x_units_text_edit)
        x_axis_layout.addLayout(x_units_layout)

        x_range_layout = QHBoxLayout()
        self.x_start_label = QLabel("X Start:")
        self.x_start_spinbox = QDoubleSpinBox()
        self.x_stop_label = QLabel("X Stop:")
        self.x_stop_spinbox = QDoubleSpinBox()
        x_range_layout.addWidget(self.x_start_label)
        x_range_layout.addWidget(self.x_start_spinbox)
        x_range_layout.addWidget(self.x_stop_label)
        x_range_layout.addWidget(self.x_stop_spinbox)
        x_axis_layout.addLayout(x_range_layout)

        self.x_axis_group_box.setLayout(x_axis_layout)
        self.layout.addWidget(self.x_axis_group_box)

        # Y-Axis Group Box
        self.y_axis_group_box = QGroupBox("Y-Axis")
        y_axis_layout = QVBoxLayout()

        self.y_grid_checkbox = QCheckBox("Y Grid")
        self.y_grid_checkbox.setChecked(True)
        self.y_grid_checkbox.stateChanged.connect(lambda state: self.yGridChanged.emit(state == 2))
        y_axis_layout.addWidget(self.y_grid_checkbox)

        self.y_log_scale_checkbox = QCheckBox("Y Log Scale")
        self.y_log_scale_checkbox.stateChanged.connect(lambda state: self.yLogScaleToggled.emit(state == 2))
        y_axis_layout.addWidget(self.y_log_scale_checkbox)

        y_label_layout = QHBoxLayout()
        self.y_label_label = QLabel("Y Label:")
        self.y_label_text_edit = QLineEdit("Y")
        self.y_label_text_edit.textChanged.connect(self.yLabelChanged.emit)
        self.y_label_visibility_checkbox = QCheckBox("Show Y Label")
        self.y_label_visibility_checkbox.setChecked(False)
        self.y_label_visibility_checkbox.stateChanged.connect(lambda state: self.yLabelVisibilityChanged.emit(state == 2))
        y_label_layout.addWidget(self.y_label_label)
        y_label_layout.addWidget(self.y_label_text_edit)
        y_label_layout.addWidget(self.y_label_visibility_checkbox)
        y_axis_layout.addLayout(y_label_layout)

        y_units_layout = QHBoxLayout()
        self.y_units_label = QLabel("Y Units:")
        self.y_units_text_edit = QLineEdit("Units")
        y_units_layout.addWidget(self.y_units_label)
        y_units_layout.addWidget(self.y_units_text_edit)
        y_axis_layout.addLayout(y_units_layout)

        y_range_layout = QHBoxLayout()
        self.y_start_label = QLabel("Y Start:")
        self.y_start_spinbox = QDoubleSpinBox()
        self.y_stop_label = QLabel("Y Stop:")
        self.y_stop_spinbox = QDoubleSpinBox()
        y_range_layout.addWidget(self.y_start_label)
        y_range_layout.addWidget(self.y_start_spinbox)
        y_range_layout.addWidget(self.y_stop_label)
        y_range_layout.addWidget(self.y_stop_spinbox)
        y_axis_layout.addLayout(y_range_layout)

        self.y_axis_group_box.setLayout(y_axis_layout)
        self.layout.addWidget(self.y_axis_group_box)

        # Title Layout
        title_layout = QHBoxLayout()
        self.title_label = QLabel("Title:")
        self.title_text_edit = QLineEdit("Plot Title")
        self.title_text_edit.textChanged.connect(self.titleChanged.emit)
        self.title_visibility_checkbox = QCheckBox("Show Title")
        self.title_visibility_checkbox.setChecked(False)
        self.title_visibility_checkbox.stateChanged.connect(lambda state: self.titleVisibilityChanged.emit(state == 2))
        title_layout.addWidget(self.title_label)
        title_layout.addWidget(self.title_text_edit)
        title_layout.addWidget(self.title_visibility_checkbox)
        self.layout.addLayout(title_layout)