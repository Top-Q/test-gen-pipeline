"""Healer agent — applies minimal patches to fix test failures."""

from __future__ import annotations

from ..prompt_builder import PromptBuilder
from ..schemas.profile_schema import ProfileConfig
from .base import AgentResult, AgentRunner

HEALER_TOOLS = ["Read", "Edit", "Bash", "Glob", "Grep"]
HEALER_MODEL = "claude-sonnet-4-20250514"
HEALER_MAX_TURNS = 8


class HealerAgent:
    """Invokes Claude to patch files and fix test failures."""

    def __init__(self, profile: ProfileConfig, prompt_builder: PromptBuilder):
        self.profile = profile
        self.prompt_builder = prompt_builder
        self.runner = AgentRunner(cwd=profile.project_root)

    async def run(
        self,
        error_output: str,
        failure_category: str,
        relevant_files: list[str],
        permission_mode: str = "bypassPermissions",
    ) -> AgentResult:
        """Patch files to fix the described test failure."""
        system_prompt = self.prompt_builder.build_healer_prompt(
            error_output=error_output,
            failure_category=failure_category,
            relevant_files=relevant_files,
        )

        prompt = (
            "Fix the test failure described in the system prompt. "
            "Apply the minimal patch needed. Do NOT refactor or add features. "
            "After patching, run lint and typecheck to verify correctness."
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
