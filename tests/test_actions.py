# tests/test_actions.py
import pytest
from pymetr.state import ApplicationState
from pymetr.actions.commands import Command, ModelCommand, Result
from pymetr.actions.manager import ActionManager
from pymetr.models.base import BaseModel

# Test command implementations
class TestModel(BaseModel):
    def __init__(self, name: str, model_id: str = None):
        super().__init__(model_id)
        self.set_property('name', name)

class SetNameCommand(ModelCommand):
    def __init__(self, state: ApplicationState, model_id: str, name: str):
        super().__init__(state, model_id)
        self.new_name = name
    
    def execute(self) -> Result:
        self.store_model_state()
        model = self.state.registry.get_model(self.model_id)
        if model:
            model.set_property('name', self.new_name)
            return Result(True)
        return Result(False, error="Model not found")
    
    def undo(self) -> bool:
        return self.restore_model_state()

# Tests
@pytest.fixture
def state():
    return ApplicationState()

@pytest.fixture
def action_manager(state):
    manager = ActionManager(state)
    manager.register_command('set_name', SetNameCommand)
    return manager

def test_command_execution(state, action_manager):
    # Create model
    model = TestModel("Initial")
    state.registry.register(model)
    
    # Execute command
    result = action_manager.execute('set_name', model_id=model.id, name="Updated")
    
    # Verify execution
    assert result.success
    assert state.registry.get_model(model.id).get_property('name') == "Updated"

def test_command_undo(state, action_manager):
    # Create and register model
    model = TestModel("Initial")
    state.registry.register(model)
    
    # Execute command
    action_manager.execute('set_name', model_id=model.id, name="Updated")
    
    # Undo and verify
    result = action_manager.undo()
    assert result.success
    assert state.registry.get_model(model.id).get_property('name') == "Initial"

def test_command_redo(state, action_manager):
    # Create and register model
    model = TestModel("Initial")
    state.registry.register(model)
    
    # Execute, undo, then redo
    action_manager.execute('set_name', model_id=model.id, name="Updated")
    action_manager.undo()
    result = action_manager.redo()
    
    # Verify redo
    assert result.success
    assert state.registry.get_model(model.id).get_property('name') == "Updated"

def test_invalid_command(action_manager):
    result = action_manager.execute('unknown_command')
    assert not result.success
    assert "Unknown action" in result.error

def test_command_history_limit():
    history = CommandHistory(max_size=2)
    cmd1 = SetNameCommand(None, "id1", "name1")
    cmd2 = SetNameCommand(None, "id2", "name2")
    cmd3 = SetNameCommand(None, "id3", "name3")
    
    history.push(cmd1)
    history.push(cmd2)
    history.push(cmd3)
    
    # Verify oldest command was dropped
    assert len(history._history) == 2
    assert history._history[0] == cmd2
    assert history._history[1] == cmd3