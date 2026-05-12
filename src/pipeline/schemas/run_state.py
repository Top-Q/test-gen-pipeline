"""Run state tracking for pipeline execution."""

from __future__ import annotations

from datetime import datetime, timezone
from enum import StrEnum

from pydantic import BaseModel, Field


class PipelineState(StrEnum):
    """States in the pipeline state machine."""

    PREFLIGHT = "preflight"
    ANALYZE_PLAN = "analyze_plan"
    CHECK_POM = "check_pom"
    INVESTIGATE_DOM = "investigate_dom"
    BUILD_POM = "build_pom"
    VALIDATE_POM = "validate_pom"
    WRITE_TEST = "write_test"
    VALIDATE_TEST = "validate_test"
    RUN_TEST = "run_test"
    CLASSIFY_FAILURE = "classify_failure"
    HEAL = "heal"
    DONE = "done"
    FAILED = "failed"


class ValidationResult(BaseModel):
    """Result of a single validation check."""

    check_name: str
    passed: bool
    output: str = ""
    files_checked: list[str] = []


class TestResult(BaseModel):
    """Result of a Playwright test execution."""

    passed: bool
    total: int = 0
    failed_count: int = 0
    error_output: str = ""
    json_report: dict | None = None


class AgentInvocation(BaseModel):
    """Record of a single agent invocation."""

    agent_name: str
    state: str
    timestamp: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    success: bool = False
    files_modified: list[str] = []
    error: str = ""
    result_text: str = ""  # Full agent output — always stored for resume/re-parsing
    cost_usd: float = 0.0
    turns: int = 0
    tool_calls: list[str] = []


class FailureRecord(BaseModel):
    """Classified failure for tracking repeated errors."""

    category: str
    message: str
    file_paths: list[str] = []
    routed_to: str = ""  # "healer", "pom_builder", "abort"


class RunState(BaseModel):
    """Complete state of a pipeline run, persisted to JSON."""

    run_id: str
    profile_name: str
    test_plan_path: str
    state: PipelineState = PipelineState.PREFLIGHT
    git_branch: str = ""
    generated_po_files: list[str] = []
    generated_test_files: list[str] = []
    agent_invocations: list[AgentInvocation] = []
    validation_results: list[ValidationResult] = []
    test_results: list[TestResult] = []
    failure_history: list[FailureRecord] = []
    dom_investigation_path: str = ""
    investigator_attempts: int = 0
    pom_builder_attempts: int = 0
    test_writer_attempts: int = 0
    healer_attempts: int = 0
    created_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )
    updated_at: str = Field(
        default_factory=lambda: datetime.now(timezone.utc).isoformat()
    )

    @property
    def total_agent_invocations(self) -> int:
        return len(self.agent_invocations)

    @property
    def total_cost_usd(self) -> float:
        return sum(inv.cost_usd for inv in self.agent_invocations)

    def record_invocation(self, invocation: AgentInvocation) -> None:
        """Add an agent invocation record."""
        self.agent_invocations.append(invocation)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def record_failure(self, failure: FailureRecord) -> None:
        """Add a failure record."""
        self.failure_history.append(failure)
        self.updated_at = datetime.now(timezone.utc).isoformat()

    def has_repeated_failure(self, category: str, message: str) -> bool:
        """Check if the same failure has occurred before."""
        return any(
            f.category == category and f.message == message
            for f in self.failure_history
        )
