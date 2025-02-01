# tests/test_main_window.py
import pytest
from PySide6.QtWidgets import QApplication
from pymetr.views.windows.main_window import MainWindow, create_application
from pymetr.state import ApplicationState
from pymetr.models.base import BaseModel

class TestScript(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.fixture(scope="session")
def qapp():
    return QApplication([])

@pytest.fixture
def state():
    return ApplicationState()

@pytest.fixture
def main_window(qapp, state):
    return MainWindow(state)

def test_window_creation(main_window):
    """Test basic window creation and components"""
    # Verify core components exist
    assert main_window.tree_view is not None
    assert main_window.tab_manager is not None
    assert main_window.ribbon is not None

def test_action_handling(main_window, state, qtbot):
    """Test action handling flow"""
    # Create test script
    script = TestScript("Test Script")
    state.registry.register(script)
    
    # Select in tree
    state.set_active_model(script.id)
    
    # Track action handling
    handled_actions = []
    state.actions.execute = lambda action_id, **kwargs: handled_actions.append(action_id)
    
    # Trigger action
    main_window.ribbon.action_triggered.emit("run_script")
    
    # Verify action was handled
    assert "run_script" in handled_actions

def test_window_layout(main_window):
    """Test window layout and docking"""
    # Verify dock widget
    docks = main_window.findChildren(QDockWidget)
    assert len(docks) > 0
    assert any(d.windowTitle() == "Models" for d in docks)

def test_application_creation(state):
    """Test application creation helper"""
    app, window = create_application(state)
    
    # Verify application setup
    assert app.applicationName() == "pymetr"
    assert isinstance(window, MainWindow)