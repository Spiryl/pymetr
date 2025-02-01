# tests/test_views.py
import pytest
from pymetr.state import ApplicationState
from pymetr.views.manager import ViewManager, ViewType, ViewState
from pymetr.models.base import BaseModel

class TestModel(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.fixture
def state():
    return ApplicationState()

@pytest.fixture
def view_manager(state):
    return ViewManager(state)

def test_view_registration(state, view_manager):
    # Create model
    model = TestModel("Test")
    state.registry.register(model)
    
    # Register view
    view_state = view_manager.register_view('view1', ViewType.TREE, model.id)
    
    # Verify registration
    assert view_state.view_type == ViewType.TREE
    assert view_state.model_id == model.id
    assert not view_state.is_dirty
    
    # Verify model tracking
    assert model.id in view_manager._model_views
    assert 'view1' in view_manager._model_views[model.id]

def test_active_view(state, view_manager):
    # Create models and views
    model1 = TestModel("Test1")
    model2 = TestModel("Test2")
    state.registry.register(model1)
    state.registry.register(model2)
    
    view_manager.register_view('view1', ViewType.TREE, model1.id)
    view_manager.register_view('view2', ViewType.SCRIPT, model2.id)
    
    # Set active view
    view_manager.set_active_view('view1')
    
    # Verify active state
    assert view_manager._active_view == 'view1'
    assert view_manager._views['view1'].is_active
    assert not view_manager._views['view2'].is_active
    
    # Verify active model in state
    assert state.get_active_model().id == model1.id

def test_model_change_propagation(state, view_manager):
    # Create model and view
    model = TestModel("Test")
    state.registry.register(model)
    view_manager.register_view('view1', ViewType.TREE, model.id)
    
    # Update model
    model.set_property('name', "Updated")
    state.notify_model_changed(model.id, 'name', "Updated")
    
    # Verify view is marked dirty
    view_state = view_manager.get_view_state('view1')
    assert view_state.is_dirty

def test_model_deletion(state, view_manager):
    # Create model and views
    model = TestModel("Test")
    state.registry.register(model)
    view_manager.register_view('view1', ViewType.TREE, model.id)
    view_manager.register_view('view2', ViewType.SCRIPT, model.id)
    
    # Delete model
    state.delete_model(model.id)
    
    # Verify views are cleaned up
    assert model.id not in view_manager._model_views
    assert 'view1' not in view_manager._views
    assert 'view2' not in view_manager._views

def test_view_properties(state, view_manager):
    # Create model and view
    model = TestModel("Test")
    state.registry.register(model)
    view_manager.register_view('view1', ViewType.TREE, model.id)
    
    # Set view property
    view_manager.set_view_property('view1', 'expanded', True)
    
    # Verify property
    view_state = view_manager.get_view_state('view1')
    assert view_state.properties['expanded'] is True