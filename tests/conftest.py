# tests/conftest.py
import pytest
from PySide6.QtWidgets import QApplication
from pymetr.state import ApplicationState
from pymetr.models.base import BaseModel
from pymetr.ui.views.manager import ViewType  # Add this import
from pymetr.actions.commands import Result

# Base test models that can be used across all tests
@pytest.mark.no_collect
class TestModel(BaseModel):
    """Generic test model for testing"""
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.mark.no_collect
class TestScript(BaseModel):
    """Test script model for testing"""
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

@pytest.mark.no_collect
class TestResult(BaseModel):
    """Test result model for testing"""
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

# Fixtures that can be used across all tests
@pytest.fixture(scope="session")
def qapp():
    """Create the Qt Application"""
    return QApplication([])

@pytest.fixture
def state():
    """Create a fresh application state for each test"""
    return ApplicationState()

@pytest.fixture
def test_model(state):
    """Create a test model and register it with the state"""
    model = TestModel("Test Model")
    state.registry.register(model)
    return model

@pytest.fixture
def test_script(state):
    """Create a test script and register it with the state"""
    script = TestScript("Test Script")
    state.registry.register(script)
    return script

@pytest.fixture
def test_result(state):
    """Create a test result and register it with the state"""
    result = TestResult("Test Result")
    state.registry.register(result)
    return result

@pytest.fixture
def success_result():
    """Fixture for successful command result"""
    return Result(success=True)

@pytest.fixture
def failed_result():
    """Fixture for failed command result"""
    return Result(success=False, error="Test error")