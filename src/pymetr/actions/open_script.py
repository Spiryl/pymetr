# src/pymetr/actions/open_script.py
from pymetr.actions.commands import Command, Result
from pathlib import Path
from PySide6.QtWidgets import QFileDialog, QApplication
from pymetr.models.test_script import TestScript
from pymetr.logging import logger

class OpenScriptCommand(Command):
    """Command to open a test script file"""
    
    def execute(self) -> Result:
        logger.info("Executing OpenScriptCommand")
        # Show file dialog
        file_path, _ = QFileDialog.getOpenFileName(
            QApplication.activeWindow(),
            "Open Test Script",
            "",
            "Python Files (*.py)"
        )
        
        if not file_path:
            logger.debug("No file selected")
            return Result(False, error="No file selected")
            
        try:
            script_path = Path(file_path)
            logger.debug(f"Creating TestScript model for: {script_path}")
            
            # Create TestScript model
            testScript = TestScript(
                name=script_path.stem,
                script_path=script_path
            )
            
            # Register in state
            script = self.state.create_model(testScript)
            logger.info(f"Registered script with ID: {script.id}")
            
            # Set as active model
            self.state.set_active_model(script.id)
            
            return Result(True, data={"script_id": script.id})
            
        except Exception as e:
            logger.error(f"Failed to load script: {e}", exc_info=True)
            return Result(False, error=f"Failed to load script: {str(e)}")
    
    def undo(self) -> bool:
        return True