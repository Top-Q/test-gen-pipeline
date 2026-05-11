"""Test Writer agent — generates Playwright test spec files."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..prompt_builder import PromptBuilder
from ..schemas.profile_schema import ProfileConfig
from .base import AgentResult, AgentRunner

if TYPE_CHECKING:
    from ..reporter import PipelineReporter

TEST_WRITER_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]
TEST_WRITER_MODEL = "claude-sonnet-4-20250514"
TEST_WRITER_MAX_TURNS = 20


class TestWriterAgent:
    """Invokes Claude to generate Playwright test files."""

    def __init__(
        self,
        profile: ProfileConfig,
        prompt_builder: PromptBuilder,
        reporter: PipelineReporter | None = None,
    ):
        self.profile = profile
        self.prompt_builder = prompt_builder
        self.runner = AgentRunner(cwd=profile.project_root, reporter=reporter)

    async def run(
        self,
        test_plan_text: str,
        pom_contracts_json: str,
        permission_mode: str = "bypassPermissions",
    ) -> AgentResult:
        """Generate test spec files for the given test plan and POM contracts."""
        system_prompt = self.prompt_builder.build_test_writer_prompt(
            test_plan_text=test_plan_text,
            pom_contracts_json=pom_contracts_json,
        )

        prompt = (
            "Write Playwright test files (.spec.ts) for all scenarios in the test plan. "
            "Use the POM contracts provided — do NOT call methods that don't exist. "
            "After writing, run lint and typecheck to verify correctness."
        )

        return await self.runner.invoke(
            agent_name="test_writer",
            prompt=prompt,
            system_prompt=system_prompt,
            tools=TEST_WRITER_TOOLS,
            model=TEST_WRITER_MODEL,
            max_turns=TEST_WRITER_MAX_TURNS,
            permission_mode=permission_mode,
        )
