import logging
logger = logging.getLogger(__name__)

from PySide6.QtWidgets import QHBoxLayout, QToolButton
from PySide6.QtWidgets import QWidget, QSpacerItem, QSizePolicy, QMenu
from PySide6.QtWidgets import QComboBox, QWidgetAction, QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt, QSize
from PySide6.QtCore import Signal, Qt, QPoint
from PySide6.QtGui import QAction, QIcon


class TitleBar(QWidget):
    plotModeChanged = Signal(str)
    roiPlotToggled = Signal(bool)
    testTraceClicked = Signal()
    screenshotClicked = Signal()
    groupTraces = Signal()
    isolateTraces = Signal()
    traceModeChanged = Signal(str)
    clearTraces = Signal()
    icon_path = "pymetr/application/icons/"

    def __init__(self, parent=None):
        super(TitleBar, self).__init__(parent)
        self.layout = QHBoxLayout(self)
        self.layout.setContentsMargins(5, 0, 5, 0)
        self.layout.setSpacing(10)
        self.color_palette = ['#FFAA00', '#4BFF36', '#F23CA6', '#FF9535', '#02FEE4', '#2F46FA', '#FFFE13', '#55FC77']

        # Create and configure each button separately
        self.file_button = QToolButton(self)
        self.file_button.setText("File")
        self.layout.addWidget(self.file_button)  # Add to layout

        self.report_button = QToolButton(self)
        self.report_button.setText("Report")
        self.layout.addWidget(self.report_button)  # Add to layout

        self.automation_button = QToolButton(self)
        self.automation_button.setText("Automation")
        self.layout.addWidget(self.automation_button)  # Add to layout

        self.window_button = QToolButton(self)
        self.window_button.setText("Window")
        self.layout.addWidget(self.window_button)  # Add to layout

        # Plot mode combo box
        self.plot_mode_combo_box = QComboBox()
        self.plot_mode_combo_box.addItems(["Single", "Stack", "Run"])
        self.plot_mode_combo_box.currentTextChanged.connect(self.on_plot_mode_changed)

        # ROI plot action
        self.roi_plot_action = QAction(QIcon(f"{self.icon_path}region_g.png"), "Region Plot", self)
        self.roi_plot_action.setCheckable(True)
        self.roi_plot_action.toggled.connect(self.on_roi_plot_toggled)
        self.roi_plot_button = QToolButton(self)
        self.roi_plot_button.setDefaultAction(self.roi_plot_action)

        # Screenshot action
        self.screenshot_action = QAction(QIcon(f"{self.icon_path}camera.png"), "Screenshot", self)
        self.screenshot_action.triggered.connect(self.on_screenshot_clicked)
        self.screenshot_button = QToolButton(self)
        self.screenshot_button.setDefaultAction(self.screenshot_action)

        self.trace_mode_combo = QComboBox()
        self.trace_mode_combo.addItems(["Group", "Isolate"])
        self.trace_mode_combo.currentTextChanged.connect(self.on_trace_mode_changed)

        self.group_all_button = QToolButton(self)
        self.group_all_button.setIcon(QIcon("pymetr/application/icons/group.png"))
        self.group_all_button.clicked.connect(self.on_group_all_clicked)

        self.isolate_all_button = QToolButton(self)
        self.isolate_all_button.setIcon(QIcon("pymetr/application/icons/isolate.png"))
        self.isolate_all_button.clicked.connect(self.on_isolate_all_clicked)

        self.clear_traces_button = QToolButton(self)
        self.clear_traces_button.setIcon(QIcon("pymetr/application/icons/clear.png"))
        self.clear_traces_button.clicked.connect(self.on_clear_traces_clicked)

        # Test trace action
        self.test_trace_action = QAction(QIcon(f"{self.icon_path}lab_g.png"), "Test Trace", self)
        self.test_trace_action.triggered.connect(self.on_test_trace_clicked)
        self.test_trace_button = QToolButton(self)
        self.test_trace_button.setDefaultAction(self.test_trace_action)

        # Spacer that pushes the control buttons to the right
        spacer = QSpacerItem(40, 10, QSizePolicy.Expanding, QSizePolicy.Minimum)

        # Window control buttons using icons
        self.minimize_button = QToolButton()
        self.minimize_button.setIcon(QIcon(f"{self.icon_path}minimize.png"))
        self.minimize_button.setIconSize(QSize(20, 20))  # Adjust size as needed

        self.maximize_button = QToolButton()
        self.maximize_button.setIcon(QIcon(f"{self.icon_path}maximize.png"))
        self.maximize_button.setIconSize(QSize(20, 20))  # Adjust size as needed

        self.close_button = QToolButton()
        self.close_button.setIcon(QIcon(f"{self.icon_path}close.png"))
        self.close_button.setIconSize(QSize(20, 20))  # Adjust size as needed

        self.minimize_button.clicked.connect(parent.showMinimized)
        self.maximize_button.clicked.connect(parent.showMaximized)
        self.close_button.clicked.connect(parent.close)

        # Adding widgets to the layout
        self.layout.addWidget(self.file_button)
        self.layout.addWidget(self.report_button)
        self.layout.addWidget(self.automation_button)
        self.layout.addWidget(self.window_button)
        self.layout.addWidget(self.plot_mode_combo_box)
        self.layout.addWidget(self.roi_plot_button)
        self.layout.addWidget(self.screenshot_button)
        self.layout.addWidget(self.trace_mode_combo)
        self.layout.addWidget(self.group_all_button)
        self.layout.addWidget(self.isolate_all_button)
        self.layout.addWidget(self.clear_traces_button)
        self.layout.addWidget(self.test_trace_button)
        self.layout.addSpacerItem(spacer)
        self.layout.addWidget(self.minimize_button)
        self.layout.addWidget(self.maximize_button)
        self.layout.addWidget(self.close_button)

        self.setLayout(self.layout)

    def on_trace_mode_changed(self, mode):
        self.traceModeChanged.emit(mode)

    def on_group_all_clicked(self):
        self.groupTraces.emit()

    def on_isolate_all_clicked(self):
        self.isolateTraces.emit()

    def on_clear_traces_clicked(self):
        self.clearTraces.emit()
        
    def show_file_menu(self):
        menu = QMenu(self)
        menu.setStyleSheet('''
            QMenu {
                background-color: #2A2A2A;
                border: 1px solid #3E3E3E;
            }
            QMenu::item {
                padding: 8px 12px;
                background-color: transparent;
                color: #AAAAAA;
            }
            QMenu::item:selected {
                background-color: #FFAA00;
                color: #FFFFFF;
            }
        ''')

        # Create a QTreeWidget as the central widget of the menu
        tree_widget = QTreeWidget(menu)
        tree_widget.setHeaderHidden(True)
        tree_widget.setRootIsDecorated(False)
        tree_widget.setExpandsOnDoubleClick(False)

        # Create QTreeWidgetItem for each file action
        export_item = QTreeWidgetItem(["Export Plot"])
        export_item.setIcon(0, QIcon("path/to/export_icon.png"))
        export_item.setData(0, Qt.UserRole, self.export_plot)

        generate_report_item = QTreeWidgetItem(["Generate Report"])
        generate_report_item.setIcon(0, QIcon("path/to/report_icon.png"))
        generate_report_item.setData(0, Qt.UserRole, self.generate_report)

        import_item = QTreeWidgetItem(["Import Trace Data"])
        import_item.setIcon(0, QIcon("path/to/import_icon.png"))
        import_item.setData(0, Qt.UserRole, self.import_trace_data)

        tree_widget.addTopLevelItems([export_item, generate_report_item, import_item])

        # Connect itemClicked signal to handle action triggering
        tree_widget.itemClicked.connect(self.trigger_file_action)

        # Set the QTreeWidget as the central widget of the menu
        menu_widget = QWidgetAction(menu)
        menu_widget.setDefaultWidget(tree_widget)
        menu.addAction(menu_widget)

        # Show the menu at the button's position
        menu.exec(self.file_menu_button.mapToGlobal(QPoint(0, self.file_menu_button.height())))

    def trigger_file_action(self, item, column):
        action = item.data(0, Qt.UserRole)
        if action:
            action()

    def export_plot(self):
        print("Exporting plot...")

    def generate_report(self):
        print("Generating report...")

    def import_trace_data(self):
        print("Importing trace data...")

    def on_plot_mode_changed(self, plot_mode):
        self.plotModeChanged.emit(plot_mode)

    def on_roi_plot_toggled(self, checked):
        if checked:
            self.roi_plot_action.setIcon(QIcon("pymetr/application/icons/region.png"))
        else:
            self.roi_plot_action.setIcon(QIcon("pymetr/application/icons/region_g.png"))
        self.roiPlotToggled.emit(checked)

    def on_screenshot_clicked(self):
        self.screenshotClicked.emit()

    def on_test_trace_clicked(self):
        self.testTraceClicked.emit()

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.start = self.mapToGlobal(event.position().toPoint())
            self.pressing = True

    def mouseMoveEvent(self, event):
        if self.pressing and event.buttons() & Qt.LeftButton:
            end = self.mapToGlobal(event.position().toPoint())
            movement = end - self.start
            self.parent().move(self.parent().pos() + movement)
            self.start = end

    def mouseReleaseEvent(self, event):
        self.pressing = False