# tests/test_actions.py
import pytest
from pymetr.actions.commands import Command, ModelCommand, Result
from pymetr.actions.manager import ActionManager
from .conftest import TestModel
from pymetr.state import ApplicationState

class SetNameCommand(ModelCommand):
    def __init__(self, state: 'ApplicationState', model_id: str, name: str):
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

def test_command_execution(state, test_model):
    action_manager = ActionManager(state)
    action_manager.register_command('set_name', SetNameCommand)
    
    result = action_manager.execute('set_name', model_id=test_model.id, name="Updated")
    
    assert result.success
    assert state.registry.get_model(test_model.id).get_property('name') == "Updated"

def test_command_undo(state, test_model):
    action_manager = ActionManager(state)
    action_manager.register_command('set_name', SetNameCommand)
    
    original_name = test_model.get_property('name')
    action_manager.execute('set_name', model_id=test_model.id, name="Updated")
    
    result = action_manager.undo()
    assert result.success
    assert state.registry.get_model(test_model.id).get_property('name') == original_name