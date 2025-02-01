# tests/test_tab_manager.py
import pytest
from PySide6.QtWidgets import QApplication, QWidget
from pymetr.views.widgets.tab_manager import TabManager
from pymetr.state import ApplicationState
from pymetr.models.base import BaseModel
from pymetr.views.manager import ViewType

# Mock view classes for testing
class MockScriptView(QWidget):
    def __init__(self, state, model_id, parent=None):
        super().__init__(parent)
        self.state = state
        self.model_id = model_id

class MockResultView(QWidget):
    def __init__(self, state, model_id, parent=None):
        super().__init__(parent)
        self.state = state
        self.model_id = model_id

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
def tab_manager(qapp, state):
    manager = TabManager(state)
    # Override view creation for testing
    manager._create_view = lambda model_id, view_type: (
        MockScriptView(state, model_id) if view_type == ViewType.SCRIPT
        else MockResultView(state, model_id) if view_type == ViewType.RESULT
        else None
    )
    return manager

def test_tab_creation(state, tab_manager):
    # Create test script
    script = TestScript("Test Script")
    state.registry.register(script)
    
    # Simulate active model change
    state.set_active_model(script.id)
    
    # Verify tab creation
    assert script.id in tab_manager._tabs
    assert isinstance(tab_manager._tabs[script.id], MockScriptView)
    assert tab_manager.currentWidget() == tab_manager._tabs[script.id]

def test_tab_switching(state, tab_manager):
    # Create two models
    script = TestScript("Script")
    result = TestResult("Result")
    state.registry.register(script)
    state.registry.register(result)
    
    # Activate first model
    state.set_active_model(script.id)
    first_tab = tab_manager.currentWidget()
    
    # Activate second model
    state.set_active_model(result.id)
    second_tab = tab_manager.currentWidget()
    
    # Verify different tabs
    assert first_tab != second_tab
    assert isinstance(first_tab, MockScriptView)
    assert isinstance(second_tab, MockResultView)

def test_tab_close(state, tab_manager, qtbot):
    # Create model
    script = TestScript("Test")
    state.registry.register(script)
    state.set_active_model(script.id)
    
    # Close tab
    tab_index = tab_manager.indexOf(tab_manager._tabs[script.id])
    tab_manager._handle_tab_close(tab_index)
    
    # Verify tab closed
    assert script.id not in tab_manager._tabs
    assert tab_manager.count() == 0

def test_model_deletion(state, tab_manager):
    # Create model
    script = TestScript("Test")
    state.registry.register(script)
    state.set_active_model(script.id)
    
    # Delete model
    state.delete_model(script.id)
    
    # Verify tab cleanup
    assert script.id not in tab_manager._tabs
    assert tab_manager.count() == 0