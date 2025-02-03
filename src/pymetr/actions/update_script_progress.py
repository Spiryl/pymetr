# src/pymetr/actions/update_script_progress.py
from pymetr.actions.commands import Command, Result
from pymetr.models.test_script import TestScript
from pymetr.logging import logger

class UpdateScriptProgressCommand(Command):
    """Command to update script progress and status"""
    def execute(self, test_id: str, percent: float = None, status: str = None, message: str = "") -> Result:
        """Update script progress or status"""
        logger.info(f"Updating script {test_id}: progress={percent}%, status={status}, message={message}")
        
        script = self.state.registry.get_model(test_id)
        if not script:
            return Result(False, error=f"No script found with ID: {test_id}")
            
        if not isinstance(script, TestScript):
            return Result(False, error=f"Model {test_id} is not a TestScript")
            
        try:
            if percent is not None:
                logger.debug(f"Setting progress for {test_id} to {percent}%")
                script.progress = percent
                self.state.notify_model_changed(test_id, 'progress', percent)
                
            if status is not None:
                logger.debug(f"Setting status for {test_id} to {status}")
                script.status = status
                self.state.notify_model_changed(test_id, 'status', status)
                
                # Auto-complete progress for final states
                if status in ['Pass', 'Fail', 'Error', 'Complete'] and script.progress < 100:
                    logger.debug(f"Auto-completing progress for {test_id}")
                    script.progress = 100
                    self.state.notify_model_changed(test_id, 'progress', 100)
            
            if message:
                script._progress_message = message
                
            return Result(True)
            
        except Exception as e:
            logger.error(f"Error updating script {test_id}: {e}", exc_info=True)
            return Result(False, error=str(e))
    
    def undo(self) -> bool:
        """Progress updates cannot be undone"""
        return False