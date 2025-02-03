# engine.py
from PySide6.QtCore import QThread, Signal, QObject, Qt, QEventLoop, QTimer
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, TYPE_CHECKING
import importlib.util
from pathlib import Path
import traceback
import numpy as np
import pandas as pd

from pymetr.logging import logger
from pymetr.models import TestScript, TestResult

if TYPE_CHECKING:
    from pymetr.state import ApplicationState


class ScriptRunner(QThread):
    """
    Handles script execution in a separate thread.
    
    Signals:
        finished(bool, str): Emitted when script finishes (success, error_message)
        error(str, str, str): Emitted for script errors (error_type, message, traceback)
    """
    finished = Signal(bool, str)  # success, error_message
    error = Signal(str, str, str)  # error_type, message, traceback

    def __init__(self, script_path: Path, globals_dict: dict):
        super().__init__()
        self.script_path = script_path
        self.globals_dict = globals_dict.copy()  # Make a copy to avoid shared dict issues
        self.result = None

    def run(self):
        try:
            # Load the script module
            logger.debug(f"Loading script: {self.script_path}")
            spec = importlib.util.spec_from_file_location(
                self.script_path.stem, 
                self.script_path
            )
            if not spec or not spec.loader:
                raise FileNotFoundError(f"Cannot load spec for {self.script_path}")

            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            logger.debug("Script module loaded successfully.")

            # Check for and execute run_test()
            if not hasattr(module, "run_test"):
                raise AttributeError("Script must contain a run_test() function")

            # Update module globals and run
            logger.debug("Executing run_test() function")
            module.__dict__.update(self.globals_dict)
            self.result = module.run_test()
            
            # Handle the result
            if isinstance(self.result, bool):
                logger.debug(f"Script completed with explicit result: {self.result}")
            else:
                logger.debug("Script completed without explicit pass/fail")
                self.result = True  # Consider it a pass if no boolean result
                
            self.finished.emit(True, "")

        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            error_tb = traceback.format_exc()
            
            logger.exception(f"Script execution error: {error_msg}")
            self.error.emit(error_type, error_msg, error_tb)
            self.finished.emit(False, error_msg)

        finally:
            # Clean up any resources if needed
            self.globals_dict.clear()


class Engine(QObject):
    """
    Orchestrates script execution and provides script environment.
    
    Signals:
        script_started(str): Emitted when script starts (test_id)
        script_finished(str, bool, str): Emitted when script finishes (test_id, success, error_msg)
    """
    
    progressChanged = Signal(str, float, str)  # test_id, percent, message
    script_started = Signal(str)  # test_id
    script_finished = Signal(str, bool, str)  # test_id, success, error_msg

    def __init__(self, state: "ApplicationState"):
        super().__init__()
        self.state = state
        self.running: bool = False
        self._instruments: Dict[str, Any] = {}
        self._current_test_id: Optional[str] = None
        
        # Timer for elapsed time updates
        self._elapsed_timer: Optional[QTimer] = None
        self._start_time: Optional[datetime] = None
        
        # Provide script-level helper functions
        self.script_globals = {
            "get_dut": self.get_dut,
            "get_instrument": self.get_instrument,
            "set_test_progress": self.set_test_progress,
            "set_test_status": self.set_test_status,
            "new_result": self.new_result,
            "wait": self.wait,
            "np": np,
            "pd": pd,
        }

        logger.debug(f"Script globals: {list(self.script_globals.keys())}")
        logger.info("Engine initialized successfully.")

    def get_dut(self, model: Optional[str] = None) -> Optional[Any]:
        """Returns the current DUT from ApplicationState, optionally checking model."""
        dut = self.state.get_dut()
        if dut and model and dut.model != model:
            logger.warning(f"Requested DUT model '{model}' != current DUT '{dut.model}'. Returning None.")
            return None
        return dut

    def get_instrument(self, model: str) -> Optional[Any]:
        """Retrieve (or create) an instrument instance by 'model'."""
        if model in self._instruments:
            return self._instruments[model]

        try:
            inst = self._create_instrument(model)
            if inst:
                inst.open()
                self._instruments[model] = inst
                logger.debug(f"Created and opened instrument '{model}'")
            return inst
        except Exception as e:
            logger.exception(f"Error creating instrument '{model}': {e}")
            return None

    def _create_instrument(self, model: str) -> Optional[Any]:
        """Create a new instrument instance."""
        if model == "MockInstrument":
            return MockInstrument(resource_name="MOCK::INSTR")
        logger.warning(f"Unknown instrument model requested: '{model}'")
        return None

    def set_test_progress(self, percent: float, message: str = ""):
        """Progress update from running script."""
        if not self._current_test_id:
            logger.warning("set_test_progress called but no current test!")
            return
        logger.debug(f"Progress update: {percent}% - {message}")
        self.progressChanged.emit(self._current_test_id, percent, message)

    def set_test_status(self, status: str):
        """Update test status."""
        test_obj = self._get_current_test()
        if test_obj:
            test_obj.status = status

    def new_result(self, name: str) -> Optional[TestResult]:
        """Create a new test result."""
        test_obj = self._get_current_test()
        if not test_obj:
            logger.warning("No active test found; cannot create new_result.")
            return None

        result = TestResult(name=name)
        test_obj.add_result(result)
        return result

    def run_test_script(self, test_id: str) -> None:
        """Runs the test script in a separate thread."""
        test_obj = self.state.find_test_by_id(test_id)
        if not test_obj or not test_obj.script_path:
            logger.error(f"Cannot run script: No test found for ID '{test_id}' or missing script path.")
            return

        self._current_test_id = test_id
        test_obj.status = "Running"
        self.script_started.emit(test_id)
        self.running = True

        # Start elapsed time tracking.
        self._start_time = datetime.now()
        self._start_elapsed_timer()

        self.script_runner = ScriptRunner(test_obj.script_path, self.script_globals)

        def on_script_finished(success: bool, error_msg: str):
            """Handle script completion."""
            # Stop the elapsed timer if it is running.
            self._stop_elapsed_timer()

            if success:
                result = self.script_runner.result
                # Use 'Pass' if result is True, otherwise mark as 'Complete'.
                test_obj.status = "Pass" if isinstance(result, bool) and result else "Complete"
            else:
                test_obj.status = "Error"
                if test_obj.results:
                    # Assuming test_obj.results is a dict-like collection.
                    current_result = list(test_obj.results.values())[-1]
                    current_result.set_error({
                        "message": error_msg,
                        "type": "Error",
                        "traceback": traceback.format_exc()
                    })

            self.running = False
            self.script_runner = None
            self.script_finished.emit(test_id, success, error_msg)

        self.script_runner.finished.connect(on_script_finished)
        self.script_runner.start()

    def _start_elapsed_timer(self):
        """Starts a QTimer to update elapsed time every second."""
        if self._elapsed_timer is not None:
            self._elapsed_timer.stop()
            self._elapsed_timer.deleteLater()

        self._elapsed_timer = QTimer(self)
        self._elapsed_timer.setInterval(1000)  # 1 second
        self._elapsed_timer.timeout.connect(self._update_elapsed_time)
        self._elapsed_timer.start()
        logger.debug("Elapsed time timer started.")

    def _stop_elapsed_timer(self):
        """Stops and cleans up the elapsed time timer."""
        if self._elapsed_timer is not None:
            self._elapsed_timer.stop()
            self._elapsed_timer.deleteLater()
            self._elapsed_timer = None
            logger.debug("Elapsed time timer stopped.")

    def _update_elapsed_time(self):
        """Called by the timer to update the elapsed time for the running test."""
        if not self._current_test_id or not self._start_time:
            return

        test_obj = self.state.find_test_by_id(self._current_test_id)
        if not test_obj:
            return

        elapsed = (datetime.now() - self._start_time).total_seconds()
        # Update the test object's elapsed time. This can be done by calling a method
        # (e.g. test_obj.setElapsedTime) or by emitting a signal to update the parameter options.
        if hasattr(test_obj, "setElapsedTime"):
            test_obj.setElapsedTime(int(elapsed))
        else:
            # Alternatively, if your model supports updating options:
            test_obj.setOpts(elapsed_time=int(elapsed))
        logger.debug(f"Elapsed time updated for test {self._current_test_id}: {int(elapsed)} seconds")

    def wait(self, milliseconds: int):
        """Thread-safe wait using Qt event loop."""
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec_()

    def _get_current_test(self) -> Optional[TestScript]:
        """Return the currently active test."""
        if not self._current_test_id:
            return None
        return self.state.find_test_by_id(self._current_test_id)


# -----------------------------------------------------------------------
# MOCK INSTRUMENT CLASS
# -----------------------------------------------------------------------

class MockInstrument:
    def __init__(self, resource_name: str):
        self.resource_name = resource_name
        self.is_open = False

    def open(self):
        self.is_open = True
        logger.debug(f"MockInstrument '{self.resource_name}' opened.")

    def close(self):
        self.is_open = False
        logger.debug(f"MockInstrument '{self.resource_name}' closed.")

    def get_identity(self):
        return f"MockInstrument {self.resource_name}"
