"""Tests for the orchestrator state transitions."""

from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from pipeline.schemas.run_state import PipelineState, RunState
from pipeline.state import StateManager


@pytest.fixture
def state_manager(tmp_path: Path) -> StateManager:
    return StateManager(artifacts_dir=tmp_path)


def test_create_run(state_manager: StateManager):
    """Creating a run produces a valid initial state."""
    state = state_manager.create_run("openproject", "plan.md")

    assert state.run_id
    assert state.profile_name == "openproject"
    assert state.test_plan_path == "plan.md"
    assert state.state == PipelineState.ANALYZE_PLAN
    assert state.pom_builder_attempts == 0
    assert state.test_writer_attempts == 0
    assert state.healer_attempts == 0


def test_transition(state_manager: StateManager):
    """Transitioning updates state and persists."""
    state = state_manager.create_run("openproject", "plan.md")
    state = state_manager.transition(state, PipelineState.CHECK_POM)

    assert state.state == PipelineState.CHECK_POM


def test_load_run(state_manager: StateManager):
    """Loading a run recovers the persisted state."""
    state = state_manager.create_run("openproject", "plan.md")
    state = state_manager.transition(state, PipelineState.BUILD_POM)

    loaded = state_manager.load_run(state.run_id)
    assert loaded.state == PipelineState.BUILD_POM
    assert loaded.run_id == state.run_id


def test_load_nonexistent_run(state_manager: StateManager):
    """Loading a non-existent run raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        state_manager.load_run("nonexistent-run-id")


def test_guardrail_max_invocations():
    """RunState tracks total agent invocations."""
    state = RunState(
        run_id="test-123",
        profile_name="openproject",
        test_plan_path="plan.md",
    )
    assert state.total_agent_invocations == 0

    from pipeline.schemas.run_state import AgentInvocation

    state.record_invocation(AgentInvocation(
        agent_name="pom_builder",
        state="build_pom",
        success=True,
    ))
    assert state.total_agent_invocations == 1


def test_repeated_failure_detection():
    """RunState detects repeated identical failures."""
    state = RunState(
        run_id="test-123",
        profile_name="openproject",
        test_plan_path="plan.md",
    )

    from pipeline.schemas.run_state import FailureRecord

    state.record_failure(FailureRecord(
        category="timeout",
        message="waiting for locator('.button')",
        file_paths=["test.ts"],
        routed_to="healer",
    ))

    # First time — not repeated
    assert not state.has_repeated_failure("timeout", "some other error")

    # Same error — detected as repeated
    assert state.has_repeated_failure("timeout", "waiting for locator('.button')")
