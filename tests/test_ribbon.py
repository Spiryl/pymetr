# tests/test_ribbon.py
import pytest
from pymetr.ui.views.ribbon.context import (
    RibbonContext, DefaultContext, ScriptContext, PlotContext,
    ActionCategory, RibbonAction
)
from pymetr.ui.views.ribbon.manager import RibbonManager

def test_default_context(state, qapp):
    ribbon_manager = RibbonManager(state)
    context = DefaultContext(state)
    actions = context.get_actions()
    
    assert any(a.id == "new_script" for a in actions)
    assert any(a.category == ActionCategory.FILE for a in actions)

def test_script_context(state, qapp, test_script):
    ribbon_manager = RibbonManager(state)
    
    # Set active model
    state.set_active_model(test_script.id)
    
    assert isinstance(ribbon_manager._current_context, ScriptContext)
    actions = ribbon_manager._current_context.get_actions()
    assert any(a.id == "run_script" for a in actions)
    assert any(a.id == "stop_script" for a in actions)

def test_action_triggering(state, qapp, test_script, qtbot):
    ribbon_manager = RibbonManager(state)
    qtbot.addWidget(ribbon_manager)

    # Track triggered actions
    triggered_actions = []
    ribbon_manager.action_triggered.connect(
        lambda aid: triggered_actions.append(aid)
    )

    # Create a context with known actions
    context = ScriptContext(state)
    ribbon_manager._set_context(context)

    state.set_active_model(test_script.id)

    # Find and trigger the run action
    run_toolbar = ribbon_manager.toolbars[ActionCategory.RUN]
    run_actions = run_toolbar.actions()
    assert len(run_actions) > 0, "No actions found in RUN category"
    
    run_action = run_actions[0]
    run_action.trigger()

    assert len(triggered_actions) == 1
    assert triggered_actions[0] == "run_script"