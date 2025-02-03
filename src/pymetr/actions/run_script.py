# src/pymetr/actions/run_script.py
from pymetr.actions.commands import Command, Result
from pymetr.models.test_script import TestScript
from pymetr.logging import logger

class RunScriptCommand(Command):
    """Command to execute a test script"""
    
    def execute(self) -> Result:
        """Execute the script through the engine"""
        logger.info("Executing RunScriptCommand")
        
        # Get active model
        model = self.state.get_active_model()
        if not model:
            logger.error("No active model to run")
            return Result(False, error="No active script selected")
            
        if not isinstance(model, TestScript):
            logger.error(f"Active model is not a TestScript: {type(model)}")
            return Result(False, error="Selected item is not a script")
        
        # Validate script file exists
        if not (hasattr(model, 'script_path') and 
                model.script_path and 
                model.script_path.exists()):
            logger.error(f"Invalid script path: {getattr(model, 'script_path', None)}")
            return Result(False, error="Invalid script or missing file")
            
        try:
            logger.info(f"Running script: {model.script_path}")
            self.state.engine.run_test_script(model.id)
            return Result(True)
        except Exception as e:
            logger.error(f"Failed to run script: {e}", exc_info=True)
            return Result(False, error=f"Failed to run script: {str(e)}")
    
    def undo(self) -> bool:
        """Script execution cannot be undone"""
        return False