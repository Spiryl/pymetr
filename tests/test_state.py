# tests/test_state.py
import pytest
from pymetr.state import ApplicationState, SignalManager
from pymetr.models.base import BaseModel

class TestModel(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.fixture
def state():
    return ApplicationState()

def test_create_model(state):
    # Create model through state
    model = state.create_model(TestModel, name="Test1")
    
    # Verify model creation and registration
    assert model.get_property('name') == "Test1"
    assert state.registry.get_model(model.id) is not None

def test_signal_emission(state):
    # Track signal emissions
    received_signals = []
    
    def handler(model_id, model_type):
        received_signals.append((model_id, model_type))
    
    # Connect handler
    state.signals.connect('model_created', handler)
    
    # Create model and verify signal
    model = state.create_model(TestModel, name="Test1")
    assert len(received_signals) == 1
    assert received_signals[0][1] == "TestModel"

def test_active_model(state):
    # Create models
    model1 = state.create_model(TestModel, name="Test1")
    model2 = state.create_model(TestModel, name="Test2")
    
    # Track active model changes
    changes = []
    state.signals.connect('active_model_changed', 
                         lambda new_id, old_id: changes.append((new_id, old_id)))
    
    # Set and verify active model
    state.set_active_model(model1.id)
    assert state.get_active_model().id == model1.id
    assert len(changes) == 1
    
    # Change active model
    state.set_active_model(model2.id)
    assert state.get_active_model().id == model2.id
    assert len(changes) == 2

def test_model_relationships(state):
    # Create models
    parent = state.create_model(TestModel, name="Parent")
    child = state.create_model(TestModel, name="Child")
    
    # Track relationship signals
    links = []
    state.signals.connect('models_linked', 
                         lambda pid, cid: links.append(('link', pid, cid)))
    state.signals.connect('models_unlinked', 
                         lambda pid, cid: links.append(('unlink', pid, cid)))
    
    # Create and verify relationship
    state.link_models(parent.id, child.id)
    children = state.get_model_children(parent.id)
    assert len(children) == 1
    assert children[0].get_property('name') == "Child"
    assert len(links) == 1
    assert links[0][0] == 'link'
    
    # Remove and verify relationship
    state.unlink_models(parent.id, child.id)
    assert len(state.get_model_children(parent.id)) == 0
    assert len(links) == 2
    assert links[1][0] == 'unlink'

def test_model_deletion(state):
    # Create model
    model = state.create_model(TestModel, name="Test")
    
    # Track deletion signals
    deletions = []
    state.signals.connect('model_deleting', 
                         lambda mid, mtype: deletions.append(('deleting', mid)))
    state.signals.connect('model_deleted', 
                         lambda mid: deletions.append(('deleted', mid)))
    
    # Delete and verify
    state.delete_model(model.id)
    assert state.registry.get_model(model.id) is None
    assert len(deletions) == 2
    assert deletions[0][0] == 'deleting'
    assert deletions[1][0] == 'deleted'