# tests/test_views.py
import pytest
from pymetr.ui.views.manager import ViewManager, ViewType, ViewState

def test_view_registration(state, test_script):  # Added test_script fixture
    view_manager = ViewManager(state)
    
    # Register view for test model
    view_state = view_manager.register_view(
        'view1',
        ViewType.SCRIPT,
        test_script.id
    )
    
    assert view_state.view_type == ViewType.SCRIPT
    assert view_state.model_id == test_script.id
    assert not view_state.is_dirty
    assert test_script.id in view_manager._model_views

def test_active_view(state, test_script, test_result):  # Using both fixtures
    view_manager = ViewManager(state)
    
    # Register two views
    view_manager.register_view('view1', ViewType.SCRIPT, test_script.id)
    view_manager.register_view('view2', ViewType.RESULT, test_result.id)
    
    # Set active view
    view_manager.set_active_view('view1')
    
    # Verify active states
    assert view_manager._active_view == 'view1'
    assert view_manager._views['view1'].is_active
    assert not view_manager._views['view2'].is_active
    
    # Verify active model in state
    assert state.get_active_model().id == test_script.id

def test_model_change_propagation(state, test_script):  # Added test_script fixture
    view_manager = ViewManager(state)
    view_manager.register_view('view1', ViewType.SCRIPT, test_script.id)
    
    # Update model
    test_script.set_property('name', "Updated")
    state.notify_model_changed(test_script.id, 'name', "Updated")
    
    # Verify view is marked dirty
    view_state = view_manager.get_view_state('view1')
    assert view_state.is_dirty

def test_model_deletion(state, test_script):  # Added test_script fixture
    view_manager = ViewManager(state)
    
    # Register two views for same model
    view_manager.register_view('view1', ViewType.SCRIPT, test_script.id)
    view_manager.register_view('view2', ViewType.SCRIPT, test_script.id)
    
    # Delete model
    state.delete_model(test_script.id)
    
    # Verify views are cleaned up
    assert test_script.id not in view_manager._model_views
    assert 'view1' not in view_manager._views
    assert 'view2' not in view_manager._views

def test_view_properties(state, test_script):  # Added test_script fixture
    view_manager = ViewManager(state)
    view_manager.register_view('view1', ViewType.SCRIPT, test_script.id)
    
    # Set view property
    view_manager.set_view_property('view1', 'cursor_position', 100)
    
    # Verify property
    view_state = view_manager.get_view_state('view1')
    assert view_state.properties['cursor_position'] == 100