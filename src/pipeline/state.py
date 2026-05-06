"""Run state persistence — JSON-based state management with crash recovery."""

import json
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from .schemas.run_state import PipelineState, RunState

ARTIFACTS_DIR = Path(__file__).parent.parent.parent / "artifacts"


class StateManager:
    """Manages pipeline run state with JSON persistence."""

    def __init__(self, artifacts_dir: Path | None = None):
        self.artifacts_dir = artifacts_dir or ARTIFACTS_DIR

    def create_run(
        self,
        profile_name: str,
        test_plan_path: str,
    ) -> RunState:
        """Create a new run with a unique ID and persist initial state."""
        now = datetime.now(timezone.utc)
        short_uuid = uuid4().hex[:8]
        run_id = f"{now.strftime('%Y%m%d-%H%M%S')}-{short_uuid}"

        state = RunState(
            run_id=run_id,
            profile_name=profile_name,
            test_plan_path=test_plan_path,
            state=PipelineState.ANALYZE_PLAN,
        )

        self._persist(state)
        return state

    def transition(
        self,
        state: RunState,
        new_state: PipelineState,
        **updates: object,
    ) -> RunState:
        """Transition to a new state, apply updates, and persist."""
        state.state = new_state
        state.updated_at = datetime.now(timezone.utc).isoformat()

        for key, value in updates.items():
            if hasattr(state, key):
                setattr(state, key, value)

        self._persist(state)
        return state

    def load_run(self, run_id: str) -> RunState:
        """Load a run state from disk for crash recovery / resume."""
        state_file = self._state_file(run_id)
        if not state_file.exists():
            raise FileNotFoundError(f"Run state not found: {state_file}")

        data = json.loads(state_file.read_text(encoding="utf-8"))
        return RunState(**data)

    def _persist(self, state: RunState) -> None:
        """Write state to JSON file."""
        state_file = self._state_file(state.run_id)
        state_file.parent.mkdir(parents=True, exist_ok=True)
        state_file.write_text(
            state.model_dump_json(indent=2),
            encoding="utf-8",
        )

    def _state_file(self, run_id: str) -> Path:
        """Path to a run's state file."""
        return self.artifacts_dir / run_id / "run_state.json"
