"""Click-based CLI for the test generation pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import sys
from pathlib import Path

import click

from .orchestrator import Orchestrator
from .state import StateManager

logger = logging.getLogger(__name__)


def _setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s %(levelname)-8s %(name)s: %(message)s",
        stream=sys.stderr,
    )


@click.group()
@click.option("--verbose", "-v", is_flag=True, help="Enable debug logging")
def main(verbose: bool) -> None:
    """Agentic Playwright test generation pipeline."""
    _setup_logging(verbose)


@main.command()
@click.option("--profile", "-p", required=True, help="Profile name (e.g. openproject)")
@click.option("--plan", required=True, type=click.Path(exists=True), help="Path to test plan .md file")
@click.option("--ci", is_flag=True, help="CI mode: bypass all permission prompts")
@click.option("--resume", "resume_id", default=None, help="Resume a failed run by ID")
@click.option("--profiles-dir", default=None, type=click.Path(exists=True), help="Custom profiles directory")
@click.option("--artifacts-dir", default=None, type=click.Path(), help="Custom artifacts directory")
def run(
    profile: str,
    plan: str,
    ci: bool,
    resume_id: str | None,
    profiles_dir: str | None,
    artifacts_dir: str | None,
) -> None:
    """Run the full pipeline: POM build, test write, execute, heal."""
    profiles_path = Path(profiles_dir) if profiles_dir else None
    artifacts_path = Path(artifacts_dir) if artifacts_dir else None

    orchestrator = Orchestrator(
        profile_name=profile,
        test_plan_path=plan,
        ci_mode=ci,
        profiles_dir=profiles_path,
        artifacts_dir=artifacts_path,
    )

    # Resume from existing state if requested
    resume_state = None
    if resume_id:
        state_mgr = StateManager(artifacts_path)
        resume_state = state_mgr.load_run(resume_id)
        click.echo(f"Resuming run {resume_id} from state {resume_state.state}", err=True)

    final_state = asyncio.run(orchestrator.run(resume_state))

    # Output result
    click.echo(f"Run {final_state.run_id}: {final_state.state}", err=True)
    if final_state.git_branch:
        click.echo(f"Branch: {final_state.git_branch}", err=True)

    # JSON result to stdout
    click.echo(final_state.model_dump_json(indent=2))

    sys.exit(0 if final_state.state == "done" else 1)


@main.command("build-pom")
@click.option("--profile", "-p", required=True, help="Profile name")
@click.option("--plan", required=True, type=click.Path(exists=True), help="Path to test plan .md file")
@click.option("--ci", is_flag=True, help="CI mode")
@click.option("--profiles-dir", default=None, type=click.Path(exists=True))
def build_pom(profile: str, plan: str, ci: bool, profiles_dir: str | None) -> None:
    """Run only the POM Builder step."""
    from .pom_contract_extractor import contracts_to_json, extract_contracts_from_dir
    from .profile import load_profile
    from .prompt_builder import PromptBuilder
    from .agents.pom_builder import PomBuilderAgent
    from .test_plan_parser import parse_test_plan
    from .orchestrator import _format_test_plan_summary

    profiles_path = Path(profiles_dir) if profiles_dir else None
    prof = load_profile(profile, profiles_path)
    test_plan = parse_test_plan(plan)
    prompt_builder = PromptBuilder(prof)
    agent = PomBuilderAgent(prof, prompt_builder)

    summary = _format_test_plan_summary(test_plan)
    po_base = prof.resolve_path(prof.po_base_dir)
    existing = extract_contracts_from_dir(po_base, prof.project_root)
    existing_json = contracts_to_json(existing) if existing else ""

    permission = "bypassPermissions" if ci else "acceptEdits"
    result = asyncio.run(agent.run(summary, existing_json, permission))

    click.echo(json.dumps({"success": result.success, "files": result.files_modified}, indent=2))
    sys.exit(0 if result.success else 1)


@main.command("write-test")
@click.option("--profile", "-p", required=True, help="Profile name")
@click.option("--plan", required=True, type=click.Path(exists=True), help="Path to test plan .md file")
@click.option("--ci", is_flag=True, help="CI mode")
@click.option("--profiles-dir", default=None, type=click.Path(exists=True))
def write_test(profile: str, plan: str, ci: bool, profiles_dir: str | None) -> None:
    """Run only the Test Writer step."""
    from .pom_contract_extractor import contracts_to_json, extract_contracts_from_dir
    from .profile import load_profile
    from .prompt_builder import PromptBuilder
    from .agents.test_writer import TestWriterAgent
    from .test_plan_parser import parse_test_plan

    profiles_path = Path(profiles_dir) if profiles_dir else None
    prof = load_profile(profile, profiles_path)
    test_plan = parse_test_plan(plan)
    prompt_builder = PromptBuilder(prof)
    agent = TestWriterAgent(prof, prompt_builder)

    po_base = prof.resolve_path(prof.po_base_dir)
    contracts = extract_contracts_from_dir(po_base, prof.project_root)
    contracts_json = contracts_to_json(contracts)
    plan_text = Path(plan).read_text(encoding="utf-8")

    permission = "bypassPermissions" if ci else "acceptEdits"
    result = asyncio.run(agent.run(plan_text, contracts_json, permission))

    click.echo(json.dumps({"success": result.success, "files": result.files_modified}, indent=2))
    sys.exit(0 if result.success else 1)


@main.command()
@click.option("--profile", "-p", required=True, help="Profile name")
@click.option("--files", required=True, help="Glob or space-separated file paths to validate")
@click.option("--profiles-dir", default=None, type=click.Path(exists=True))
def validate(profile: str, files: str, profiles_dir: str | None) -> None:
    """Run deterministic validation on specified files."""
    from .profile import load_profile
    from .validator import run_all_checks

    profiles_path = Path(profiles_dir) if profiles_dir else None
    prof = load_profile(profile, profiles_path)
    file_list = files.split()

    results = asyncio.run(run_all_checks(prof, file_list))

    for r in results:
        status = "PASS" if r.passed else "FAIL"
        click.echo(f"[{status}] {r.check_name}", err=True)
        if not r.passed:
            click.echo(f"  {r.output}", err=True)

    all_passed = all(r.passed for r in results)
    sys.exit(0 if all_passed else 1)


@main.command()
@click.option("--profile", "-p", required=True, help="Profile name")
@click.option("--run-id", required=True, help="Run ID to heal")
@click.option("--ci", is_flag=True, help="CI mode")
@click.option("--profiles-dir", default=None, type=click.Path(exists=True))
@click.option("--artifacts-dir", default=None, type=click.Path())
def heal(profile: str, run_id: str, ci: bool, profiles_dir: str | None, artifacts_dir: str | None) -> None:
    """Run the Healer on a failed run."""
    from .profile import load_profile
    from .prompt_builder import PromptBuilder
    from .agents.healer import HealerAgent

    profiles_path = Path(profiles_dir) if profiles_dir else None
    artifacts_path = Path(artifacts_dir) if artifacts_dir else None

    prof = load_profile(profile, profiles_path)
    state_mgr = StateManager(artifacts_path)
    state = state_mgr.load_run(run_id)

    if not state.failure_history:
        click.echo("No failures recorded in this run", err=True)
        sys.exit(1)

    last_failure = state.failure_history[-1]
    last_test = state.test_results[-1] if state.test_results else None
    error_output = last_test.error_output if last_test else last_failure.message

    prompt_builder = PromptBuilder(prof)
    agent = HealerAgent(prof, prompt_builder)

    permission = "bypassPermissions" if ci else "acceptEdits"
    result = asyncio.run(agent.run(
        error_output=error_output,
        failure_category=last_failure.category,
        relevant_files=last_failure.file_paths,
        permission_mode=permission,
    ))

    click.echo(json.dumps({"success": result.success, "files": result.files_modified}, indent=2))
    sys.exit(0 if result.success else 1)
