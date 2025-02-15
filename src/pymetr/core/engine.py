# engine.py
from PySide6.QtCore import QObject, Signal, QThread, QTimer, QEventLoop
from datetime import datetime
from pathlib import Path
import importlib.util
import sys
import traceback

import numpy as np
import pandas as pd

from pymetr.core.logging import logger
from pymetr.models.test import TestScript, TestGroup, TestResult
from pymetr.models.plot import Plot
from pymetr.models.trace import Trace
from pymetr.models.measurement import Measurement
from pymetr.models.table import DataTable


class ScriptRunner(QThread):
    # Signal: finished(success, error_message)
    finished = Signal(bool, str)
    # Optional error signal: error(error_type, error_msg, traceback)
    error = Signal(str, str, str)
    
    def __init__(self, script_path: Path, globals_dict: dict):
        super().__init__()
        self.script_path = script_path
        self.globals_dict = globals_dict.copy()
        
    def run(self):
        try:
            spec = importlib.util.spec_from_file_location(self.script_path.stem, str(self.script_path))
            if spec is None or spec.loader is None:
                raise ImportError(f"Cannot load script: {self.script_path}")
            module = importlib.util.module_from_spec(spec)
            sys.modules[spec.name] = module
            spec.loader.exec_module(module)
            
            if not hasattr(module, "run_test"):
                raise AttributeError("Script must contain a run_test() function")
                
            module.__dict__.update(self.globals_dict)
            result = module.run_test()
            # If run_test() does not return a bool, treat it as success
            if not isinstance(result, bool):
                result = True
            self.finished.emit(result, "")
        except Exception as e:
            error_type = type(e).__name__
            error_msg = str(e)
            error_tb = traceback.format_exc()
            logger.error(f"ScriptRunner error: {error_tb}")
            self.error.emit(error_type, error_msg, error_tb)
            self.finished.emit(False, error_msg)
        finally:
            self.globals_dict.clear()
            
    def stop(self):
        self.terminate()
        self.wait()


class Engine(QObject):
    # Signals for script running (active script) events
    script_started = Signal(str)               # Emits the running TestScript's ID
    script_finished = Signal(str, bool, str)   # (script_id, success, error_msg)
    progress_changed = Signal(str, float, str) # (script_id, percent, message)
    
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.script_runner = None
        self.start_time = None
        
        # Timer to update elapsed time every second while a script is running
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)
        
        # Inject only helper functions (and libraries like np, pd) for scripts
        self.globals = {
            "create_group": self.create_group,
            "create_result": self.create_result,
            "create_plot": self.create_plot,
            "create_table": self.create_table,
            "set_test_progress": self.set_test_progress,
            "wait": self.wait,
            "np": np,
            "pd": pd,
        }
        
        logger.info("Engine initialized.")

    # ---------------------------------------------------
    # Script Running
    # ---------------------------------------------------

    def run_test_script(self, script_id: str) -> None:
        """
        Run a test script using the specified TestScript model ID.
        
        - Retrieves the TestScript model from the state
        - Sets it as the active test in the ApplicationState
        - Calls on_started() on the model
        - Launches a ScriptRunner thread to execute the script
        """
        script = self.state.get_model(script_id)
        if not script or not isinstance(script, TestScript):
            logger.error(f"Engine.run_test_script: No TestScript found with id '{script_id}'.")
            return

        # Clear previous child models to avoid name collisions and stale views.
        self.state.clear_children(script.id)
        
        self.state.set_active_test(script_id)
        script.on_started()
        self.script_started.emit(script.id)

        self.start_time = datetime.now()
        self.elapsed_timer.start()

        self.script_runner = ScriptRunner(script.script_path, self.globals)
        self.script_runner.finished.connect(self._on_script_finished)
        self.script_runner.start()
    
    def _on_script_finished(self, success: bool, error_msg: str) -> None:
        # Stop timing
        self.elapsed_timer.stop()
        
        # Retrieve whatever is currently active as the test
        test_script = self.state.get_active_test()
        if not test_script or not isinstance(test_script, TestScript):
            logger.error("Engine._on_script_finished: Active test is not a TestScript or not found.")
        else:
            # Let the script model know it has finished
            test_script.on_finished(success, error_msg)
            self.script_finished.emit(test_script.id, success, error_msg)
            logger.debug(f"Engine: TestScript '{test_script.id}' finished with success={success}")
        
        self.script_runner = None
        self.start_time = None

    # ---------------------------------------------------
    # Progress + Wait
    # ---------------------------------------------------

    def set_test_progress(self, percent: float, message: str = "") -> None:
        """
        Called by the running script to indicate progress.
        Now uses type-safe progress updates.
        """
        test_script = self.state.get_active_test()
        if test_script and isinstance(test_script, TestScript):
            # Progress will now use the float signal
            test_script.set_property('progress', float(percent))
            
            # We still want to emit our progress signal for the UI
            self.progress_changed.emit(test_script.id, float(percent), message)
    
    def wait(self, milliseconds: int) -> None:
        """
        Helper to 'sleep' in a Qt-friendly way without blocking the GUI event loop
        """
        loop = QEventLoop()
        QTimer.singleShot(milliseconds, loop.quit)
        loop.exec_()
    
    def _update_elapsed_time(self) -> None:
        """
        Update the elapsed_time on the currently active test script
        """
        if not self.start_time:
            return
        test_script = self.state.get_active_test()
        if test_script and isinstance(test_script, TestScript):
            elapsed = (datetime.now() - self.start_time).total_seconds()
            test_script.elapsed_time = int(elapsed)

    # ---------------------------------------------------
    # Create + Link Models to Active Test
    # ---------------------------------------------------

    def create_result(self, name: str) -> TestResult:
        """
        Create a TestResult and link it under the active test script
        """
        result = self.state.create_model(TestResult, name=name)
        active_test = self.state.get_active_test()
        if active_test:
            self.state.link_models(active_test.id, result.id)
        return result

    def create_group(self, name: str) -> TestGroup:
        """
        Create a TestGroup and link it under the active test script
        """
        group = self.state.create_model(TestGroup, name=name)
        active_test = self.state.get_active_test()
        if active_test:
            self.state.link_models(active_test.id, group.id)
        return group

    def create_plot(self, title: str) -> Plot:
        """
        Create a Plot and link it under the active test script
        """
        plot = self.state.create_model(Plot, title=title)
        active_test = self.state.get_active_test()
        if active_test:
            self.state.link_models(active_test.id, plot.id)
        return plot

    def create_table(self, title: str) -> DataTable:
        """
        Create a DataTable and link it under the active test script
        """
        table = self.state.create_model(DataTable, title=title)
        active_test = self.state.get_active_test()
        if active_test:
            self.state.link_models(active_test.id, table.id)
        return table
