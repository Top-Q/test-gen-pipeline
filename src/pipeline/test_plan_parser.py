"""Parser for multi-document YAML+Gherkin test plan files."""

import re
from pathlib import Path

import yaml

from .schemas.test_plan import TestPlan, TestScenario


def parse_test_plan(file_path: str | Path) -> TestPlan:
    """Parse a test plan markdown file into a TestPlan model.

    The file format is multi-document YAML separated by '---' boundaries,
    where each document contains YAML frontmatter followed by Background
    and Scenario sections in Gherkin-like syntax.
    """
    path = Path(file_path)
    content = path.read_text(encoding="utf-8")
    scenarios = _parse_documents(content)
    return TestPlan(source_file=str(path), scenarios=scenarios)


def _parse_documents(content: str) -> list[TestScenario]:
    """Split content into documents, each with YAML frontmatter + body.

    Format: ---\\n<yaml>\\n---\\n<body> separated by blank lines + ---.
    Uses regex to find each frontmatter block (---...---) followed by body text.
    """
    # Match each document: opening ---, YAML, closing ---, then body until next opening --- or EOF
    pattern = re.compile(
        r"---\s*\n(.*?)\n---\s*\n(.*?)(?=\n---\s*\n[a-zA-Z]|\Z)",
        re.DOTALL,
    )
    scenarios: list[TestScenario] = []

    for match in pattern.finditer(content):
        yaml_text = match.group(1).strip()
        body = match.group(2).strip()
        scenario = _parse_single_document_from_parts(yaml_text, body)
        if scenario:
            scenarios.append(scenario)

    return scenarios


def _parse_single_document_from_parts(yaml_text: str, body: str) -> TestScenario | None:
    """Parse a single document from pre-split YAML and body parts."""
    try:
        frontmatter = yaml.safe_load(yaml_text)
    except yaml.YAMLError:
        return None

    if not isinstance(frontmatter, dict) or "id" not in frontmatter:
        return None

    # Parse body sections
    background = _extract_section(body, "Background:")
    scenario_name, steps = _extract_scenario(body)

    return TestScenario(
        id=frontmatter["id"],
        suite=frontmatter.get("suite", ""),
        feature=frontmatter.get("feature", ""),
        component=frontmatter.get("component", ""),
        priority=frontmatter.get("priority", "P3"),
        tags=frontmatter.get("tags", []),
        variables=frontmatter.get("variables", {}),
        setup=frontmatter.get("setup", []),
        background=background,
        scenario_name=scenario_name,
        steps=steps,
    )


def _extract_section(body: str, header: str) -> str:
    """Extract a section's content (lines after header until next section)."""
    lines = body.split("\n")
    capturing = False
    section_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if stripped.startswith(header):
            capturing = True
            continue
        if capturing:
            # Stop at next section header (non-indented line ending with :)
            if stripped and not stripped.startswith(("Given", "When", "Then", "And", "But")) and stripped.endswith(":"):
                break
            section_lines.append(line)

    return "\n".join(section_lines).strip()


def _extract_scenario(body: str) -> tuple[str, list[str]]:
    """Extract scenario name and step lines from body."""
    lines = body.split("\n")
    scenario_name = ""
    steps: list[str] = []
    in_scenario = False

    for line in lines:
        stripped = line.strip()
        if stripped.startswith("Scenario:"):
            scenario_name = stripped[len("Scenario:") :].strip()
            in_scenario = True
            continue
        if in_scenario and stripped:
            # Gherkin step keywords
            if any(
                stripped.startswith(kw)
                for kw in ("Given", "When", "Then", "And", "But")
            ):
                steps.append(stripped)

    return scenario_name, steps
