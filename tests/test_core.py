# tests/test_core.py
import pytest
from pymetr.models.base import BaseModel
from pymetr.registry import ModelRegistry

class TestModel(BaseModel):
    """Test model class"""
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.fixture
def registry():
    return ModelRegistry()

def test_model_creation_and_registration(registry):
    # Create and register a model
    model = TestModel("Test1")
    registry.register(model)
    
    # Verify retrieval
    retrieved = registry.get_model(model.id)
    assert retrieved is not None
    assert retrieved.get_property('name') == "Test1"

def test_model_relationships(registry):
    # Create parent and child models
    parent = TestModel("Parent")
    child = TestModel("Child")
    
    # Register both
    registry.register(parent)
    registry.register(child)
    
    # Link them
    registry.link(parent.id, child.id)
    
    # Verify relationship
    children = registry.get_children(parent.id)
    assert len(children) == 1
    assert children[0] == child.id

def test_model_type_query(registry):
    # Create multiple models
    model1 = TestModel("Test1")
    model2 = TestModel("Test2")
    
    # Register both
    registry.register(model1)
    registry.register(model2)
    
    # Query by type
    test_models = registry.get_models_by_type(TestModel)
    assert len(test_models) == 2
    names = {m.get_property('name') for m in test_models}
    assert names == {"Test1", "Test2"}