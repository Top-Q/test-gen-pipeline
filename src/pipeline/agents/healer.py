"""Healer agent — applies minimal patches to fix test failures."""

from __future__ import annotations

from typing import TYPE_CHECKING

from ..prompt_builder import PromptBuilder
from ..schemas.profile_schema import ProfileConfig
from .base import AgentResult, AgentRunner

if TYPE_CHECKING:
    from ..reporter import PipelineReporter

HEALER_TOOLS = ["Read", "Edit", "Write", "Bash", "Glob", "Grep"]
HEALER_MODEL = "claude-sonnet-4-20250514"
HEALER_MAX_TURNS = 40


class HealerAgent:
    """Invokes Claude to patch files and fix test failures."""

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
        error_output: str,
        failure_category: str,
        relevant_files: list[str],
        test_files: list[str] | None = None,
        permission_mode: str = "bypassPermissions",
    ) -> AgentResult:
        """Patch files to fix the described test failure."""
        system_prompt = self.prompt_builder.build_healer_prompt(
            error_output=error_output,
            failure_category=failure_category,
            relevant_files=relevant_files,
            test_files=test_files or [],
        )

        files_arg = " ".join(f'"{f}"' for f in (test_files or []))
        run_cmd = f"npx playwright test {files_arg} --reporter=json" if files_arg else "npx playwright test --reporter=json"

        prompt = (
            "Follow the Required Workflow in the system prompt exactly. "
            "Step 1: Diagnose from the Error Output and error-context.md artifacts — "
            "do NOT re-run the tests. "
            "Step 2: Fix the code. "
            "Step 3: Use dom-inspect only if the artifacts lack enough info. "
            f"Step 4: Validate with lint and typecheck, then confirm with: {run_cmd}"
        )

        return await self.runner.invoke(
            agent_name="healer",
            prompt=prompt,
            system_prompt=system_prompt,
            tools=HEALER_TOOLS,
            model=HEALER_MODEL,
            max_turns=HEALER_MAX_TURNS,
            permission_mode=permission_mode,
        )
