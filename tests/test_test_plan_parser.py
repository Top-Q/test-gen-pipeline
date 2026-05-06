"""Tests for the test plan parser."""

from pathlib import Path

from pipeline.test_plan_parser import parse_test_plan


def test_parse_sample_test_plan(sample_test_plan_path: Path):
    """Parse the sample test plan and verify structure."""
    plan = parse_test_plan(sample_test_plan_path)

    assert plan.source_file == str(sample_test_plan_path)
    assert len(plan.scenarios) == 2


def test_scenario_fields(sample_test_plan_path: Path):
    """Verify individual scenario fields are parsed correctly."""
    plan = parse_test_plan(sample_test_plan_path)
    s = plan.scenarios[0]

    assert s.id == "TEST-001"
    assert s.suite == "Example"
    assert s.feature == "Example CRUD"
    assert s.component == "example"
    assert s.priority == "P1"
    assert s.tags == ["ui", "example", "regression"]
    assert "itemName" in s.variables
    assert s.scenario_name == 'Create a new example item'


def test_scenario_steps(sample_test_plan_path: Path):
    """Verify Gherkin steps are extracted."""
    plan = parse_test_plan(sample_test_plan_path)
    s = plan.scenarios[0]

    assert len(s.steps) == 2
    assert s.steps[0].startswith("When")
    assert s.steps[1].startswith("Then")


def test_scenario_with_setup(sample_test_plan_path: Path):
    """Verify setup actions are parsed."""
    plan = parse_test_plan(sample_test_plan_path)
    s = plan.scenarios[1]

    assert s.id == "TEST-002"
    assert len(s.setup) == 1
    assert "create_item" in s.setup[0]


def test_plan_components(sample_test_plan_path: Path):
    """Verify the components property."""
    plan = parse_test_plan(sample_test_plan_path)
    assert plan.components == {"example"}


def test_plan_suites(sample_test_plan_path: Path):
    """Verify the suites property."""
    plan = parse_test_plan(sample_test_plan_path)
    assert plan.suites == {"Example"}


def test_background_extracted(sample_test_plan_path: Path):
    """Verify background section is captured."""
    plan = parse_test_plan(sample_test_plan_path)
    s = plan.scenarios[0]

    assert "authenticated" in s.background
    assert "Example page" in s.background
