# tests/test_core.py
import pytest
from pymetr.registry import ModelRegistry
from .conftest import TestModel

def test_model_creation_and_registration(state):
    # Create and register a model
    model = TestModel("Test1")
    state.registry.register(model)
    
    retrieved = state.registry.get_model(model.id)
    assert retrieved is not None
    assert retrieved.get_property('name') == "Test1"

def test_model_relationships(state):
    parent = TestModel("Parent")
    child = TestModel("Child")
    
    state.registry.register(parent)
    state.registry.register(child)
    
    state.registry.link(parent.id, child.id)
    
    children = state.registry.get_children(parent.id)
    assert len(children) == 1
    assert children[0] == child.id

def test_model_type_query(state):
    model1 = TestModel("Test1")
    model2 = TestModel("Test2")
    
    state.registry.register(model1)
    state.registry.register(model2)
    
    test_models = state.registry.get_models_by_type(TestModel)
    assert len(test_models) == 2
    names = {m.get_property('name') for m in test_models}
    assert names == {"Test1", "Test2"}