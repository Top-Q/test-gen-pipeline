"""Test plan and scenario schemas parsed from YAML+Gherkin markdown."""

from pydantic import BaseModel


class TestScenario(BaseModel):
    """A single test scenario parsed from the test plan document."""

    id: str
    suite: str
    feature: str
    component: str
    priority: str  # P1, P2, etc.
    tags: list[str] = []
    variables: dict[str, str] = {}
    setup: list[dict] = []  # e.g. [{"invite_member": {"email": "...", "role": "..."}}]
    background: str = ""  # raw Background section text
    scenario_name: str = ""
    steps: list[str] = []  # individual Gherkin step lines


class TestPlan(BaseModel):
    """A collection of test scenarios from a single test plan file."""

    source_file: str
    scenarios: list[TestScenario]

    @property
    def components(self) -> set[str]:
        """Unique component names referenced in the plan."""
        return {s.component for s in self.scenarios}

    @property
    def suites(self) -> set[str]:
        """Unique suite names referenced in the plan."""
        return {s.suite for s in self.scenarios}
