# tests/test_tree_view.py
import pytest
from pymetr.views.widgets.tree_view import ModelTreeView
from .conftest import TestScript, TestResult

def test_model_creation(state, qapp, test_script):
    tree_view = ModelTreeView(state)
    
    # Emit model created signal
    state.signals.emit('model_created', test_script.id, type(test_script).__name__)
    
    # Verify tree node created
    assert test_script.id in tree_view._item_map
    item = tree_view._item_map[test_script.id]
    assert '📝' in item.text(0)  # Script icon
    assert "Test Script" in item.text(0)

def test_model_hierarchy(state, qapp, test_script, test_result):
    tree_view = ModelTreeView(state)
    
    # Emit creation signals
    state.signals.emit('model_created', test_script.id, type(test_script).__name__)
    state.signals.emit('model_created', test_result.id, type(test_result).__name__)
    
    # Link models
    state.signals.emit('models_linked', test_script.id, test_result.id)
    
    # Verify hierarchy
    script_item = tree_view._item_map[test_script.id]
    result_item = tree_view._item_map[test_result.id]
    assert result_item.parent() == script_item

def test_selection_signal(state, qapp, test_script, qtbot):
    tree_view = ModelTreeView(state)
    state.signals.emit('model_created', test_script.id, type(test_script).__name__)
    
    # Track selection signal
    with qtbot.wait_signal(tree_view.selection_changed) as blocker:
        item = tree_view._item_map[test_script.id]
        item.setSelected(True)
    
    assert blocker.args == [test_script.id]

def test_selection_triggers_tab_and_context(state, qapp, test_script, qtbot):
    """Test that selecting an item updates tabs and context"""
    tree_view = ModelTreeView(state)
    qtbot.addWidget(tree_view)
    
    # Track selection signal
    selection_signals = []
    tree_view.selection_changed.connect(lambda mid: selection_signals.append(mid))
    
    # Create and select item
    state.signals.emit('model_created', test_script.id, type(test_script).__name__)
    
    # Get the created item and select it
    item = tree_view._item_map[test_script.id]
    tree_view.setCurrentItem(item)
    
    # Verify selection was handled
    assert len(selection_signals) > 0
    assert selection_signals[-1] == test_script.id
    assert state.get_active_model().id == test_script.id