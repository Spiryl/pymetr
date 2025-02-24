# tests/test_tab_manager.py
import pytest
from PySide6.QtWidgets import QWidget
from pymetr.ui.views.tab_manager import TabManager
from pymetr.ui.views.manager import ViewType

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

def test_tab_creation(state, qapp, test_script):
    tab_manager = TabManager(state)
    # Override view creation for testing
    tab_manager._create_view = lambda model_id, view_type: (
        MockScriptView(state, model_id) if view_type == ViewType.SCRIPT
        else MockResultView(state, model_id)
    )
    
    # Simulate active model change
    state.set_active_model(test_script.id)
    
    assert test_script.id in tab_manager._tabs
    assert isinstance(tab_manager._tabs[test_script.id], MockScriptView)
    assert tab_manager.currentWidget() == tab_manager._tabs[test_script.id]

def test_tab_switching(state, qapp, test_script, test_result):
    tab_manager = TabManager(state)
    tab_manager._create_view = lambda model_id, view_type: (
        MockScriptView(state, model_id) if view_type == ViewType.SCRIPT
        else MockResultView(state, model_id) if view_type == ViewType.RESULT
        else None
    )
    
    # Activate first model
    state.set_active_model(test_script.id)
    first_tab = tab_manager.currentWidget()
    
    # Activate second model
    state.set_active_model(test_result.id)
    second_tab = tab_manager.currentWidget()
    
    assert first_tab != second_tab
    assert isinstance(first_tab, MockScriptView)
    assert isinstance(second_tab, MockResultView)