"""Investigator agent — navigates the site and writes a DOM investigation report."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..prompt_builder import PromptBuilder
from ..schemas.profile_schema import ProfileConfig
from .base import AgentResult, AgentRunner

if TYPE_CHECKING:
    from ..reporter import PipelineReporter

INVESTIGATOR_TOOLS = ["Bash", "Write", "Read"]
INVESTIGATOR_MODEL = "claude-sonnet-4-20250514"
INVESTIGATOR_MAX_TURNS = 60


class InvestigatorAgent:
    """Invokes Claude to navigate the site and write a DOM investigation report."""

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
        test_plan_summary: str,
        output_path: str,
        permission_mode: str = "bypassPermissions",
    ) -> AgentResult:
        """Navigate the site and write a DOM investigation report to output_path."""
        system_prompt = self.prompt_builder.build_investigator_prompt(
            test_plan_summary=test_plan_summary,
            output_path=output_path,
        )

        prompt = f"Navigate the site and write the DOM investigation report to: {output_path}"

        result = await self.runner.invoke(
            agent_name="investigator",
            prompt=prompt,
            system_prompt=system_prompt,
            tools=INVESTIGATOR_TOOLS,
            model=INVESTIGATOR_MODEL,
            max_turns=INVESTIGATOR_MAX_TURNS,
            permission_mode=permission_mode,
        )

        # Verify the report file was actually created and is non-empty
        report_path = Path(output_path)
        if result.success and (not report_path.exists() or report_path.stat().st_size == 0):
            return AgentResult(
                agent_name="investigator",
                success=False,
                result_text=result.result_text + "\n[FAILED: Report file missing or empty]",
                files_modified=result.files_modified,
                cost_usd=result.cost_usd,
                turns=result.turns,
                tool_calls=result.tool_calls,
            )

        return result
