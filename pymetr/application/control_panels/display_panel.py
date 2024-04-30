# --- display_panel.py ---
from PySide6.QtWidgets import QWidget, QHBoxLayout, QVBoxLayout, QGroupBox, QCheckBox, QLineEdit, QComboBox, QLabel
from PySide6.QtCore import Signal

class DisplayPanel(QWidget):
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

        # Plot Settings Group Box
        self.plot_settings_group_box = QGroupBox("Plot Settings")
        plot_settings_layout = QVBoxLayout()

        self.grid_checkbox = QCheckBox("Grid")
        self.grid_checkbox.stateChanged.connect(lambda state: self.gridToggled.emit(state == 2))
        plot_settings_layout.addWidget(self.grid_checkbox)

        self.x_log_scale_checkbox = QCheckBox("X Log Scale")
        self.x_log_scale_checkbox.stateChanged.connect(lambda state: self.xLogScaleToggled.emit(state == 2))
        plot_settings_layout.addWidget(self.x_log_scale_checkbox)

        self.y_log_scale_checkbox = QCheckBox("Y Log Scale")
        self.y_log_scale_checkbox.stateChanged.connect(lambda state: self.yLogScaleToggled.emit(state == 2))
        plot_settings_layout.addWidget(self.y_log_scale_checkbox)

        self.x_grid_checkbox = QCheckBox("X Grid")
        self.x_grid_checkbox.setChecked(True)
        self.x_grid_checkbox.stateChanged.connect(lambda state: self.xGridChanged.emit(state == 2))
        plot_settings_layout.addWidget(self.x_grid_checkbox)

        self.y_grid_checkbox = QCheckBox("Y Grid")
        self.y_grid_checkbox.setChecked(True)
        self.y_grid_checkbox.stateChanged.connect(lambda state: self.yGridChanged.emit(state == 2))
        plot_settings_layout.addWidget(self.y_grid_checkbox)

        self.plot_settings_group_box.setLayout(plot_settings_layout)
        self.layout.addWidget(self.plot_settings_group_box)

        # Labels Group Box
        self.labels_group_box = QGroupBox("Labels")
        labels_layout = QVBoxLayout()

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
        labels_layout.addLayout(title_layout)

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
        labels_layout.addLayout(x_label_layout)

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
        labels_layout.addLayout(y_label_layout)

        self.labels_group_box.setLayout(labels_layout)
        self.layout.addWidget(self.labels_group_box)