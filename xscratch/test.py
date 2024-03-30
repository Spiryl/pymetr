from PySide6.QtWidgets import QApplication, QVBoxLayout, QWidget
from pyqtgraph.parametertree import Parameter, ParameterTree

# Define the function to be called when the action parameter is activated
def action_callback():
    print("Action parameter triggered")

# Define a function to handle changes to the parameter value
def value_changed(param, value):
    print(f"Parameter {param.name()} changed to {value}")

# Create the application instance
app = QApplication([])

# Define parameters, including an action parameter and a value parameter in separate groups
params = [
    {'name': 'Action Parameters', 'type': 'group', 'children': [
        {'name': 'Action', 'type': 'action'},
    ]},
    {'name': 'Value Parameters', 'type': 'group', 'children': [
        {'name': 'Some Value', 'type': 'int', 'value': 10, 'limits': (0, 100)},
    ]}
]

# Create ParameterTree
param_tree = ParameterTree()
parameters = Parameter.create(name='params', type='group', children=params)
param_tree.setParameters(parameters, showTop=False)

# Retrieve the action parameter and connect the action
action_param = parameters.child('Action Parameters', 'Action')
action_param.sigActivated.connect(action_callback)

# Retrieve the value parameter and connect the change handler
value_param = parameters.child('Value Parameters', 'Some Value')
value_param.sigValueChanged.connect(value_changed)

# Setup the layout and widget
widget = QWidget()
layout = QVBoxLayout()
layout.addWidget(param_tree)
widget.setLayout(layout)

# Show the widget
widget.show()

# Execute the application
app.exec_()