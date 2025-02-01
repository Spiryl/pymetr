# tests/test_tree_view.py
import pytest
from PySide6.QtWidgets import QApplication
from pymetr.views.widgets.tree_view import ModelTreeView, ModelTreeItem
from pymetr.state import ApplicationState
from pymetr.models.base import BaseModel

# Need QApplication for widget tests
@pytest.fixture(scope="session")
def qapp():
    return QApplication([])

class TestScript(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

class TestResult(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.fixture
def state():
    return ApplicationState()

@pytest.fixture
def tree_view(qapp, state):
    return ModelTreeView(state)

def test_model_creation(state, tree_view):
    # Create test script
    script = TestScript("Test Script")
    state.registry.register(script)
    state.signals.emit('model_created', script.id, type(script).__name__)
    
    # Verify tree node created
    assert script.id in tree_view._item_map
    item = tree_view._item_map[script.id]
    assert isinstance(item, ModelTreeItem)
    assert '📝' in item.text(0)
    assert "Test Script" in item.text(0)

def test_model_hierarchy(state, tree_view):
    # Create parent and child
    script = TestScript("Parent Script")
    result = TestResult("Child Result")
    
    state.registry.register(script)
    state.registry.register(result)
    
    state.signals.emit('model_created', script.id, type(script).__name__)
    state.signals.emit('model_created', result.id, type(result).__name__)
    
    # Link models
    state.signals.emit('models_linked', script.id, result.id)
    
    # Verify hierarchy
    script_item = tree_view._item_map[script.id]
    result_item = tree_view._item_map[result.id]
    assert result_item.parent() == script_item

def test_model_rename(state, tree_view):
    # Create model
    script = TestScript("Original")
    state.registry.register(script)
    state.signals.emit('model_created', script.id, type(script).__name__)
    
    # Change name
    script.set_property('name', "Updated")
    state.signals.emit('model_changed', script.id, 'name', "Updated")
    
    # Verify update
    item = tree_view._item_map[script.id]
    assert "Updated" in item.text(0)
    assert '📝' in item.text(0)

def test_selection_signal(state, tree_view, qtbot):
    # Create model
    script = TestScript("Test")
    state.registry.register(script)
    state.signals.emit('model_created', script.id, type(script).__name__)
    
    # Track selection signal
    with qtbot.wait_signal(tree_view.selection_changed) as blocker:
        item = tree_view._item_map[script.id]
        item.setSelected(True)
    
    # Verify signal emission
    assert blocker.args == [script.id]