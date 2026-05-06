"""Prompt builder — Jinja2-based rendering of agent prompts from profiles."""

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader

from .profile import load_knowledge_content
from .schemas.profile_schema import ProfileConfig

TEMPLATES_DIR = Path(__file__).parent.parent.parent / "prompt-templates"


class PromptBuilder:
    """Builds agent prompts by rendering Jinja2 templates with profile context."""

    def __init__(
        self,
        profile: ProfileConfig,
        templates_dir: Path | None = None,
    ):
        self.profile = profile
        self.templates_dir = templates_dir or TEMPLATES_DIR
        self._env = Environment(
            loader=FileSystemLoader(str(self.templates_dir)),
            keep_trailing_newline=True,
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self._knowledge = load_knowledge_content(profile.knowledge_files)

    def render(self, template_name: str, **extra_context: Any) -> str:
        """Render a template with profile config, knowledge, and extra context."""
        template = self._env.get_template(template_name)
        context = {
            "profile": self.profile,
            "knowledge": self._knowledge,
            **extra_context,
        }
        return template.render(context)

    def build_pom_builder_prompt(
        self,
        test_plan_summary: str,
        existing_po_summary: str = "",
    ) -> str:
        """Build the system prompt for the POM Builder agent."""
        return self.render(
            "pom_builder.md.j2",
            test_plan_summary=test_plan_summary,
            existing_po_summary=existing_po_summary,
        )

    def build_test_writer_prompt(
        self,
        test_plan_text: str,
        pom_contracts_json: str,
    ) -> str:
        """Build the system prompt for the Test Writer agent."""
        return self.render(
            "test_writer.md.j2",
            test_plan_text=test_plan_text,
            pom_contracts_json=pom_contracts_json,
        )

    def build_healer_prompt(
        self,
        error_output: str,
        failure_category: str,
        relevant_files: list[str],
    ) -> str:
        """Build the system prompt for the Healer agent."""
        return self.render(
            "healer.md.j2",
            error_output=error_output,
            failure_category=failure_category,
            relevant_files=relevant_files,
        )
