# tests/test_state.py
import pytest
from pymetr.state import ApplicationState, SignalManager
from .conftest import TestModel

def test_create_model(state):
    model = state.create_model(TestModel, name="Test1")
    assert model.get_property('name') == "Test1"
    assert state.registry.get_model(model.id) is not None

def test_signal_emission(state):
    received_signals = []
    
    def handler(model_id, model_type):
        received_signals.append((model_id, model_type))
    
    state.signals.connect('model_created', handler)
    model = state.create_model(TestModel, name="Test1")
    
    assert len(received_signals) == 1
    assert received_signals[0][1] == "TestModel"

def test_active_model(state):
    model1 = state.create_model(TestModel, name="Test1")
    model2 = state.create_model(TestModel, name="Test2")
    
    changes = []
    state.signals.connect('active_model_changed', 
                         lambda new_id, old_id: changes.append((new_id, old_id)))
    
    state.set_active_model(model1.id)
    assert state.get_active_model().id == model1.id
    assert len(changes) == 1
    
    state.set_active_model(model2.id)
    assert state.get_active_model().id == model2.id
    assert len(changes) == 2