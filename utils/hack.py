import sys
import logging
from PySide6 import QtWidgets
import pyqtgraph.parametertree as pt
from pyqtgraph.parametertree import Parameter, ParameterItem, registerParameterType

logging.basicConfig(level=logging.DEBUG, format="%(asctime)s [%(levelname)s] %(message)s")

class MyCustomProgressItem(ParameterItem):
    def __init__(self, param, depth):
        super().__init__(param, depth)
        self.widget = None
        self.hideWidget = False  # Important: Keep widget visible always

    def makeWidget(self):
        if self.widget is None:
            self.widget = QtWidgets.QProgressBar()
            self.widget.setMaximumHeight(20)
            self.widget.setMinimum(0)
            self.widget.setMaximum(100)
            self.widget.sigChanged = self.widget.valueChanged
            
            # Apply custom color if provided
            barColor = self.param.opts.get("barColor", None)
            if barColor:
                self.widget.setStyleSheet("QProgressBar::chunk { background-color: %s; }" % barColor)
                logging.debug("Custom bar color applied: %s", barColor)
                
        return self.widget

    def valueChanged(self, param, val):
        if self.widget is not None:
            self.widget.setValue(val)

    def treeWidgetChanged(self):
        # Call the parent implementation
        super().treeWidgetChanged()
        
        # Create widget if it doesn't exist
        if self.widget is None:
            self.widget = self.makeWidget()
            
        # Add widget to tree
        tree = self.treeWidget()
        if tree is not None and self.widget is not None:
            tree.setItemWidget(self, 1, self.widget)
            
        # Set initial value
        if self.param.hasValue():
            self.valueChanged(self.param, self.param.value())

class MyCustomProgress(Parameter):
    itemClass = MyCustomProgressItem

# Register the custom parameter type
registerParameterType("mycustomprogress", MyCustomProgress, override=True)

def main():
    app = QtWidgets.QApplication(sys.argv)
    tree = pt.ParameterTree()
    tree.setWindowTitle("Custom Parameter Example")
    tree.resize(600, 200)

    # Define parameters
    params = [
        dict(name="builtin", type="progress", title="Built-in Progress", value=40, suffix="%"),
        dict(name="custom", type="mycustomprogress", title="Custom Progress", value=70, barColor="purple", suffix="%")
    ]
    
    p = Parameter.create(name="Progress Examples", type="group", children=params)
    tree.setParameters(p, showTop=False)
    
    # Ensure column 1 is wide enough
    tree.header().resizeSection(1, 200)
    
    tree.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main()