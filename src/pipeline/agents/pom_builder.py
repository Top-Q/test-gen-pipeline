"""POM Builder agent — generates Page Objects and Components."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..prompt_builder import PromptBuilder
from ..schemas.profile_schema import ProfileConfig
from .base import AgentResult, AgentRunner

if TYPE_CHECKING:
    from ..reporter import PipelineReporter

POM_BUILDER_TOOLS = ["Read", "Write", "Edit", "Glob", "Grep", "Bash"]
POM_BUILDER_MODEL = "claude-sonnet-4-20250514"
POM_BUILDER_MAX_TURNS = 60


class PomBuilderAgent:
    """Invokes Claude to generate Page Object / Component files."""

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
        existing_po_summary: str = "",
        dom_investigation: str = "",
        permission_mode: str = "bypassPermissions",
    ) -> AgentResult:
        """Generate PO/component files for the given test plan."""
        system_prompt = self.prompt_builder.build_pom_builder_prompt(
            test_plan_summary=test_plan_summary,
            existing_po_summary=existing_po_summary,
            dom_investigation=dom_investigation,
        )

        prompt = (
            "Generate the Page Object and Component files needed for the test scenarios "
            "described in the system prompt. Follow all architecture rules strictly. "
            "After writing the files, run lint and typecheck to verify correctness."
        )

        return await self.runner.invoke(
            agent_name="pom_builder",
            prompt=prompt,
            system_prompt=system_prompt,
            tools=POM_BUILDER_TOOLS,
            model=POM_BUILDER_MODEL,
            max_turns=POM_BUILDER_MAX_TURNS,
            permission_mode=permission_mode,
        )
