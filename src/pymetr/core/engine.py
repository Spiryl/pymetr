# engine.py
from PySide6.QtCore import QObject, Signal, QThread, QTimer, QEventLoop
from datetime import datetime
from pathlib import Path
import importlib.util
import sys
import traceback
from typing import Optional
import numpy as np
import pandas as pd

from .context import TestContext
from pymetr.models import *
from pymetr.core.logging import logger

class SuiteRunner(QObject):
    """
    Handles test suite execution using run configurations.
    """
    suite_started = Signal(str)          # suite_id
    suite_completed = Signal(str, bool)  # suite_id, success
    suite_error = Signal(str, str)       # suite_id, error_msg
    script_queued = Signal(str, str)     # suite_id, script_name
    
    def __init__(self, engine):
        super().__init__()
        self._engine = engine
        self._state = engine.state
        self._current_suite = None
        self._current_config = None
        self._running = False
        self._script_queue = []
        
        # Connect to engine script signals
        self._engine.script_finished.connect(self._handle_script_completed)
    
    def run_suite(self, suite_id: str):
        """Start suite execution with active run configuration."""
        if self._running:
            logger.warning("Suite already running")
            return
            
        suite = self._state.get_model(suite_id)
        if not isinstance(suite, TestSuite):
            logger.error(f"Model {suite_id} is not a TestSuite")
            return
            
        # Get active config
        active_config_name = suite.get_property('active_config')
        config = None
        
        if active_config_name:
            # Find config by name
            for cfg in suite.get_run_configs():
                if cfg.get_property('name') == active_config_name:
                    config = cfg
                    break
        
        if not config:
            # Fallback to default config
            config = suite.get_default_config()
            if not config:
                self._handle_error("No valid run configuration found")
                return
        
        self._current_suite = suite
        self._current_config = config
        self._running = True
        
        try:
            # Build execution queue from config
            self._script_queue = config.get_execution_order()
            for script_id in self._script_queue:
                script = self._state.get_model(script_id)
                if script:
                    self.script_queued.emit(suite_id, script.get_property('name', ''))
            
            # Start first script
            self._run_next_script()
            
            # Emit started
            self.suite_started.emit(suite_id)
            suite.set_property('status', TestStatus.RUNNING)
            
        except Exception as e:
            self._handle_error(str(e))
    
    def stop_suite(self):
        """Stop current suite execution."""
        if not self._running:
            return
            
        # Stop current script
        if self._engine.script_runner:
            self._engine.script_runner.stop()
        
        self._cleanup()
    
    def _run_next_script(self):
        """Run next script in queue."""
        if not self._script_queue:
            self._handle_suite_complete(True)
            return
            
        script_id = self._script_queue.pop(0)
        try:
            # Get script model
            script = self._state.get_model(script_id)
            if not script:
                raise ValueError(f"Script {script_id} not found")
                
            # Run it
            self._engine.run_test_script(script.id)
            
        except Exception as e:
            self._handle_error(f"Failed to run script {script_id}: {e}")
    
    def _handle_script_completed(self, script_id: str, success: bool, error_msg: str):
        """Handle individual script completion."""
        if not self._running:
            return
            
        script = self._state.get_model(script_id)
        if not script:
            return
            
        if success:
            # Run next script
            self._run_next_script()
        else:
            # Check suite behavior
            behavior = self._current_suite.get_property('failure_behavior', 'stop')
            if behavior == 'stop':
                self._handle_suite_complete(False)
            else:
                # Continue with next script
                self._run_next_script()
    
    def _handle_suite_complete(self, success: bool):
        """Handle suite completion."""
        if self._current_suite:
            # Update suite status
            status = TestStatus.PASS if success else TestStatus.FAIL
            self._current_suite.set_property('status', status)
            
            # Emit completion
            self.suite_completed.emit(self._current_suite.id, success)
        
        self._cleanup()
    
    def _handle_error(self, error_msg: str):
        """Handle suite error."""
        if self._current_suite:
            self._current_suite.set_property('status', TestStatus.ERROR)
            self.suite_error.emit(self._current_suite.id, error_msg)
        
        self._cleanup()
    
    def _cleanup(self):
        """Clean up suite run state."""
        self._running = False
        self._script_queue.clear()
        self._current_suite = None
        self._current_config = None

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
                
            # Update the module's globals with our globals_dict
            module.__dict__.update(self.globals_dict)
            
            # Pass the 'test' context to run_test()
            result = module.run_test(self.globals_dict['test'])
            
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
    script_finished = Signal(str, bool, str)     # (script_id, success, error_msg)
    progress_changed = Signal(str, float, str)   # (script_id, percent, message)
    
    def __init__(self, state):
        super().__init__()
        self.state = state
        self.script_runner = None
        self.start_time = None
        
        # Timer to update elapsed time every second while a script is running
        self.elapsed_timer = QTimer(self)
        self.elapsed_timer.setInterval(1000)
        self.elapsed_timer.timeout.connect(self._update_elapsed_time)
        
        # Include numpy and pandas in globals
        self.globals = {
            'np': np,
            'pd': pd,
            'TestStatus': TestStatus,
            'ResultStatus': ResultStatus
        }

        self.state.model_changed.connect(self._handle_model_changed)
        logger.info("Engine initialized.")

    def run_suite(self, suite_id: str):
        """Run a test suite."""
        if not hasattr(self, 'suite_runner'):
            self.suite_runner = SuiteRunner(self)
        self.suite_runner.run_suite(suite_id)

    def stop_suite(self):
        """Stop current suite execution."""
        if hasattr(self, 'suite_runner'):
            self.suite_runner.stop_suite()

    def _handle_model_changed(self, model_id: str, model_type: str, prop: str, value: object):
        """
        Whenever a model changes, if it's a TestResult child of the active script,
        recalc the script's aggregated progress.
        """
        # We only care about progress changes on TestResult
        if model_type == "TestResult" and prop == "progress":
            # See if the top-level parent is a TestScript
            script = self._find_top_level_script(model_id)
            # If the script is the currently active test, recalc progress
            active_test = self.state.get_active_test()
            if script and active_test and script.id == active_test.id:
                self._update_script_progress(script)
    
    def _find_top_level_script(self, model_id: str) -> Optional[TestScript]:
        """
        Climb up the parent chain until we find a TestScript or no parent.
        """
        while True:
            parent = self.state.get_parent(model_id)
            if not parent:
                return None
            if isinstance(parent, TestScript):
                return parent
            model_id = parent.id

    def _update_script_progress(self, script: TestScript):
        """
        Compute average progress across all child TestResults
        and update the script's 'progress' property.
        """
        # Get all child models that are TestResults
        results = [
            child for child in self.state.get_children(script.id)
            if isinstance(child, TestResult)
        ]
        if not results:
            return  # No results => do nothing
        
        total = sum(r.get_property("progress", 0.0) for r in results)
        avg = total / len(results)
        
        script.set_property("progress", avg)

    # ---------------------------------------------------
    # Script Running
    # ---------------------------------------------------

    def run_test_script(self, script_id: str) -> None:
        script = self.state.get_model(script_id)
        if not script or not isinstance(script, TestScript):
            logger.error(f"Engine.run_test_script: No TestScript found with id '{script_id}'")
            return

        # Clear previous child models
        self.state.clear_children(script.id)

        # Make sure the script is "RUNNING" from the start
        script.set_property("status", "RUNNING")
        script.set_property("progress", 0)

        # Create context for this script
        context = TestContext(script, self)

        # Set as active test
        self.state.set_active_test(script_id)

        # Start execution
        context.on_script_start()
        self.script_started.emit(script.id)

        self.script_runner = ScriptRunner(script.script_path, {"test": context})
        self.script_runner.finished.connect(
            lambda success, error: self._on_script_finished(context, success, error)
        )
        self.script_runner.error.connect(
            lambda type_, msg, tb: self._on_script_error(context, type_, msg, tb)
        )
        self.script_runner.start()
    
    def _on_script_finished(self, context: TestContext, success: bool, error_msg: str) -> None:
        """Handle script completion using context."""
        if success:
            context.on_script_complete()
        else:
            context.on_script_error(error_msg)
            
        self.script_finished.emit(context.script.id, success, error_msg)
        self.script_runner = None
    
    def _on_script_error(self, context: TestContext, error_type: str, 
                        error_msg: str, traceback: str) -> None:
        """Handle script errors using context."""
        context.on_script_error(f"{error_type}: {error_msg}")
        logger.error(f"Script error: {traceback}")

    # ---------------------------------------------------
    # Helpers
    # ---------------------------------------------------

    
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

