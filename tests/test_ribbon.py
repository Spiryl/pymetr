# tests/test_ribbon.py
import pytest
from PySide6.QtWidgets import QApplication
from pymetr.views.ribbon.context import (
    RibbonContext, DefaultContext, ScriptContext, PlotContext,
    ActionCategory, RibbonAction
)
from pymetr.views.ribbon.manager import RibbonManager
from pymetr.state import ApplicationState
from pymetr.models.base import BaseModel

@pytest.fixture(scope="session")
def qapp():
    return QApplication([])

class TestScript(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.fixture
def state():
    return ApplicationState()

@pytest.fixture
def ribbon_manager(qapp, state):
    return RibbonManager(state)

def test_default_context(state, ribbon_manager):
    # Verify default context
    context = DefaultContext(state)
    actions = context.get_actions()
    
    # Should have basic file actions
    assert any(a.id == "new_script" for a in actions)
    assert any(a.category == ActionCategory.FILE for a in actions)

def test_script_context(state, ribbon_manager):
    # Create script model
    script = TestScript("Test Script")
    state.registry.register(script)
    
    # Set active model
    state.set_active_model(script.id)
    
    # Verify context switch
    assert isinstance(ribbon_manager._current_context, ScriptContext)
    
    # Verify script actions
    actions = ribbon_manager._current_context.get_actions()
    assert any(a.id == "run_script" for a in actions)
    assert any(a.id == "stop_script" for a in actions)

def test_action_triggering(state, ribbon_manager, qtbot):
    # Track triggered actions
    triggered_actions = []
    ribbon_manager.action_triggered.connect(
        lambda aid: triggered_actions.append(aid)
    )
    
    # Create and select script
    script = TestScript("Test")
    state.registry.register(script)
    state.set_active_model(script.id)
    
    # Simulate action trigger
    toolbar = ribbon_manager.toolbars[ActionCategory.RUN]
    action = toolbar.actions()[0]  # First run action
    action.trigger()
    
    # Verify action triggered
    assert len(triggered_actions) == 1
    assert triggered_actions[0] == "run_script"

def test_context_switching(state, ribbon_manager):
    # Start with default context
    assert isinstance(ribbon_manager._current_context, DefaultContext)
    
    # Switch to script context
    script = TestScript("Test")
    state.registry.register(script)
    state.set_active_model(script.id)
    assert isinstance(ribbon_manager._current_context, ScriptContext)
    
    # Back to default
    state.set_active_model(None)
    assert isinstance(ribbon_manager._current_context, DefaultContext)