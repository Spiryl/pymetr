# tests/test_main_window.py
import pytest
from PySide6.QtWidgets import QDockWidget, QMessageBox
from PySide6.QtCore import Qt
from pymetr.ui.views.windows.main_window import MainWindow
from pymetr.actions.commands import Result  # Add this import

def test_window_creation(state, qapp, qtbot):
    """Test basic window creation and components"""
    window = MainWindow(state)
    qtbot.addWidget(window)
    
    # Verify core components exist
    assert window.tree_view is not None
    assert window.tab_manager is not None
    assert window.ribbon is not None
    
    # Check tree view is properly docked
    docks = window.findChildren(QDockWidget)
    assert len(docks) > 0
    model_dock = next((d for d in docks if d.windowTitle() == "Models"), None)
    assert model_dock is not None
    assert model_dock.widget() == window.tree_view

def test_action_handling_success(state, qapp, qtbot, test_script):
    """Test successful action handling"""
    window = MainWindow(state)
    qtbot.addWidget(window)
    
    # Mock successful action execution
    state.actions.execute = lambda action_id: Result(success=True)
    
    # Trigger action
    with qtbot.wait_signal(window.ribbon.action_triggered):
        window.ribbon.action_triggered.emit("test_action")

def test_action_handling_failure(state, qapp, qtbot, monkeypatch):
    """Test failed action handling shows error message"""
    window = MainWindow(state)
    qtbot.addWidget(window)
    
    # Mock QMessageBox to capture error display
    shown_messages = []
    def mock_warning(parent, title, message):
        shown_messages.append((title, message))
    
    monkeypatch.setattr(QMessageBox, 'warning', mock_warning)
    
    # Mock failed action execution
    state.actions.execute = lambda action_id: Result(success=False, error="Test error")
    
    # Trigger action
    window.ribbon.action_triggered.emit("test_action")
    
    # Verify error was shown
    assert len(shown_messages) == 1
    assert "Action Failed" in shown_messages[0][0]
    assert "Test error" in shown_messages[0][1]

def test_window_layout_constraints(state, qapp, qtbot):
    """Test window layout and size constraints"""
    window = MainWindow(state)
    qtbot.addWidget(window)
    
    # Verify minimum size
    assert window.minimumSize().width() >= 800
    assert window.minimumSize().height() >= 600
    
    # Verify dock widget areas
    model_dock = next(d for d in window.findChildren(QDockWidget) 
                     if d.windowTitle() == "Models")
    assert model_dock.allowedAreas() & Qt.LeftDockWidgetArea
    assert model_dock.allowedAreas() & Qt.RightDockWidgetArea