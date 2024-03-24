from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget  # Or use PyQt5
from pyqtgraph.parametertree import Parameter, ParameterTree

# Define the function to be called when the action parameter is activated
def action_callback():
    print("Action parameter triggered")

# Create the application instance
app = QApplication([])

# Define parameters, including an action parameter
params = [
    {'name': 'Basic Parameters', 'type': 'group', 'children': [
        {'name': 'Action', 'type': 'action'},
    ]}
]

# Create ParameterTree
param_tree = ParameterTree()
parameters = Parameter.create(name='params', type='group', children=params)
param_tree.setParameters(parameters, showTop=False)

# Retrieve the action parameter and connect the action
action_param = parameters.child('Basic Parameters', 'Action')
action_param.sigActivated.connect(action_callback)

# Setup the layout and widget
widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(param_tree)
widget.setLayout(layout)

widget.show()

# Execute the application
app.exec_()
