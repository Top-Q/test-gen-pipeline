"""Orchestrator — state machine driving the test generation pipeline."""

from __future__ import annotations

import asyncio
import json
import logging
import re
import shutil
import urllib.error
import urllib.request
from pathlib import Path

from .agents.healer import HealerAgent, HEALER_MAX_TURNS, HEALER_MODEL
from .agents.pom_builder import PomBuilderAgent, POM_BUILDER_MAX_TURNS, POM_BUILDER_MODEL
from .agents.test_writer import TestWriterAgent, TEST_WRITER_MAX_TURNS, TEST_WRITER_MODEL
from .classifier import classify_failure
from .pom_contract_extractor import contracts_to_json, extract_contracts_from_dir
from .profile import load_profile
from .prompt_builder import PromptBuilder
from .reporter import PipelineReporter, QuietReporter
from .schemas.run_state import (
    AgentInvocation,
    FailureRecord,
    PipelineState,
    RunState,
    TestResult,
)
from .state import StateManager
from .test_plan_parser import parse_test_plan
from .validator import run_all_checks, run_lint, run_typecheck

logger = logging.getLogger(__name__)

# Guardrails
MAX_TOTAL_AGENT_INVOCATIONS = 8
MAX_POM_BUILDER_ATTEMPTS = 3
MAX_TEST_WRITER_ATTEMPTS = 3
MAX_HEALER_ATTEMPTS = 2


class Orchestrator:
    """Drives the pipeline through its state machine."""

    def __init__(
        self,
        profile_name: str,
        test_plan_path: str,
        ci_mode: bool = False,
        profiles_dir: Path | None = None,
        artifacts_dir: Path | None = None,
        reporter: PipelineReporter | None = None,
    ):
        self.profile = load_profile(profile_name, profiles_dir)
        self.test_plan = parse_test_plan(test_plan_path)
        self.ci_mode = ci_mode
        self.permission_mode = "bypassPermissions" if ci_mode else "acceptEdits"
        self.reporter: PipelineReporter = reporter or QuietReporter()

        self.state_mgr = StateManager(artifacts_dir)
        self.prompt_builder = PromptBuilder(self.profile)

        # Agents — pass reporter through
        self.pom_builder = PomBuilderAgent(self.profile, self.prompt_builder, self.reporter)
        self.test_writer = TestWriterAgent(self.profile, self.prompt_builder, self.reporter)
        self.healer = HealerAgent(self.profile, self.prompt_builder, self.reporter)

    async def run(self, resume_state: RunState | None = None) -> RunState:
        """Execute the pipeline to completion or failure."""
        self._check_playwright_cli()

        state = self.state_mgr.create_run(
            profile_name=self.profile.name,
            test_plan_path=str(self.test_plan.source_file),
        ) if resume_state is None else _recover_generated_files(resume_state)

        logger.info("Pipeline run %s starting in state %s", state.run_id, state.state)

        self.reporter.on_pipeline_start(
            run_id=state.run_id,
            profile_name=self.profile.name,
            plan_path=str(self.test_plan.source_file),
            scenarios_count=len(self.test_plan.scenarios),
            components=self.test_plan.components,
        )

        while state.state not in (PipelineState.DONE, PipelineState.FAILED):
            # Guardrail: max total agent invocations
            if state.total_agent_invocations >= MAX_TOTAL_AGENT_INVOCATIONS:
                logger.error("Max total agent invocations (%d) reached", MAX_TOTAL_AGENT_INVOCATIONS)
                state = self.state_mgr.transition(state, PipelineState.FAILED)
                break

            state = await self._step(state)

        self.reporter.on_pipeline_complete(
            final_state=state.state,
            run_id=state.run_id,
            total_cost=state.total_cost_usd,
        )

        logger.info("Pipeline run %s finished: %s", state.run_id, state.state)
        return state

    @staticmethod
    def _check_playwright_cli() -> None:
        """Warn if playwright-cli is not available on PATH."""
        if shutil.which("playwright-cli") is None:
            logger.warning(
                "playwright-cli not found on PATH. "
                "Install with: npm install -g @playwright/cli  "
                "Agents will not be able to inspect the live DOM."
            )

    async def _step(self, state: RunState) -> RunState:
        """Execute one state transition."""
        match state.state:
            case PipelineState.PREFLIGHT:
                return await self._preflight(state)
            case PipelineState.ANALYZE_PLAN:
                return await self._analyze_plan(state)
            case PipelineState.CHECK_POM:
                return await self._check_pom(state)
            case PipelineState.BUILD_POM:
                return await self._build_pom(state)
            case PipelineState.VALIDATE_POM:
                return await self._validate_pom(state)
            case PipelineState.WRITE_TEST:
                return await self._write_test(state)
            case PipelineState.VALIDATE_TEST:
                return await self._validate_test(state)
            case PipelineState.RUN_TEST:
                return await self._run_test(state)
            case PipelineState.CLASSIFY_FAILURE:
                return await self._classify_failure(state)
            case PipelineState.HEAL:
                return await self._heal(state)
            case _:
                logger.error("Unexpected state: %s", state.state)
                return self.state_mgr.transition(state, PipelineState.FAILED)

    async def _preflight(self, state: RunState) -> RunState:
        """Verify all required resources are accessible before starting the pipeline."""
        self.reporter.on_state_change(state.state, PipelineState.PREFLIGHT)
        checks_passed = True

        # 1. Source repository — project_root must exist and be a git repo
        project_root = self.profile.project_root
        if not project_root.is_dir():
            logger.error("Source repository not found: %s", project_root)
            self.reporter.on_preflight_check("source_repository", False, str(project_root))
            checks_passed = False
        elif not (project_root / ".git").exists():
            logger.error("Source repository has no .git: %s", project_root)
            self.reporter.on_preflight_check(
                "source_repository", False, f"{project_root} (no .git directory)"
            )
            checks_passed = False
        else:
            logger.info("Source repository OK: %s", project_root)
            self.reporter.on_preflight_check("source_repository", True, str(project_root))

        # 2. STD / test plan file — must still exist on disk
        plan_path = Path(self.test_plan.source_file)
        if not plan_path.is_file():
            logger.error("Test plan file not found: %s", plan_path)
            self.reporter.on_preflight_check("test_plan_file", False, str(plan_path))
            checks_passed = False
        else:
            logger.info("Test plan file OK: %s", plan_path)
            self.reporter.on_preflight_check("test_plan_file", True, str(plan_path))

        # 3. Tested site — base_url must be reachable
        base_url = self.profile.base_url
        site_ok, site_detail = await self._check_site_reachable(base_url)
        if not site_ok:
            logger.error("Site not reachable: %s — %s", base_url, site_detail)
            self.reporter.on_preflight_check("site_reachable", False, site_detail)
            checks_passed = False
        else:
            logger.info("Site reachable: %s", base_url)
            self.reporter.on_preflight_check("site_reachable", True, base_url)

        # 4. TypeScript compilation — must be clean before any agent runs
        typecheck_result = await run_typecheck(self.profile)
        state.validation_results.append(typecheck_result)
        if not typecheck_result.passed:
            first_error = typecheck_result.output.splitlines()[0] if typecheck_result.output else "unknown error"
            logger.error("Preflight typecheck failed: %s", first_error)
            self.reporter.on_preflight_check("typecheck", False, first_error)
            checks_passed = False
        else:
            logger.info("Preflight typecheck passed")
            self.reporter.on_preflight_check("typecheck", True, "OK")

        # 5. ESLint on existing source directories — must be clean before any agent runs
        source_dirs = [self.profile.po_base_dir, self.profile.test_dir]
        lint_result = await run_lint(self.profile, source_dirs)
        state.validation_results.append(lint_result)
        if not lint_result.passed:
            first_error = lint_result.output.splitlines()[0] if lint_result.output else "unknown error"
            logger.error("Preflight lint failed: %s", first_error)
            self.reporter.on_preflight_check("lint", False, first_error)
            checks_passed = False
        else:
            logger.info("Preflight lint passed")
            self.reporter.on_preflight_check("lint", True, "OK")

        if not checks_passed:
            return self.state_mgr.transition(state, PipelineState.FAILED)

        return self.state_mgr.transition(state, PipelineState.ANALYZE_PLAN)

    @staticmethod
    async def _check_site_reachable(url: str) -> tuple[bool, str]:
        """Try a HEAD request to url. Returns (reachable, detail)."""
        loop = asyncio.get_event_loop()

        def _do_request() -> tuple[bool, str]:
            try:
                req = urllib.request.Request(url, method="HEAD")
                with urllib.request.urlopen(req, timeout=10) as resp:
                    return True, f"{url} (HTTP {resp.status})"
            except urllib.error.HTTPError as e:
                # Any HTTP response means the server is up
                return True, f"{url} (HTTP {e.code})"
            except urllib.error.URLError as e:
                return False, f"{url}: {e.reason}"
            except Exception as e:  # noqa: BLE001
                return False, f"{url}: {e}"

        return await loop.run_in_executor(None, _do_request)

    async def _analyze_plan(self, state: RunState) -> RunState:
        """Parse and validate the test plan."""
        self.reporter.on_state_change(state.state, PipelineState.ANALYZE_PLAN)
        logger.info("Analyzing test plan: %d scenarios", len(self.test_plan.scenarios))

        if not self.test_plan.scenarios:
            logger.error("No scenarios found in test plan")
            return self.state_mgr.transition(state, PipelineState.FAILED)

        scenario_names = [s.scenario_name for s in self.test_plan.scenarios]
        self.reporter.on_state_change(
            state.state,
            PipelineState.ANALYZE_PLAN,
            {"info": f"{len(self.test_plan.scenarios)} scenario(s): {', '.join(scenario_names)}"},
        )

        return self.state_mgr.transition(state, PipelineState.CHECK_POM)

    async def _check_pom(self, state: RunState) -> RunState:
        """Check if required PO directories exist for the test plan's components."""
        self.reporter.on_state_change(state.state, PipelineState.CHECK_POM)
        po_base = self.profile.resolve_path(self.profile.po_base_dir)
        missing_components: list[str] = []

        for component in self.test_plan.components:
            matched = _find_po_dir(po_base, component)
            if matched is None:
                missing_components.append(component)
            elif matched.name != component:
                logger.info(
                    "Component '%s' matched existing PO directory '%s' (normalized)",
                    component, matched.name,
                )

        if missing_components:
            logger.info("Missing PO directories: %s", missing_components)
            self.reporter.on_state_change(
                state.state,
                PipelineState.CHECK_POM,
                {"info": f"Missing PO: {', '.join(missing_components)} -> build_pom"},
            )
            return await self._ensure_git_branch(
                self.state_mgr.transition(state, PipelineState.BUILD_POM)
            )

        logger.info("All PO directories exist, skipping to write_test")
        return await self._ensure_git_branch(
            self.state_mgr.transition(state, PipelineState.WRITE_TEST)
        )

    async def _ensure_git_branch(self, state: RunState) -> RunState:
        """Create a git branch if not already on one."""
        if state.git_branch:
            return state

        branch_name = f"pipeline/{state.run_id}"
        proc = await asyncio.create_subprocess_exec(
            "git", "checkout", "-b", branch_name,
            cwd=str(self.profile.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await proc.communicate()

        if proc.returncode != 0:
            logger.warning("Failed to create git branch %s (may already exist)", branch_name)
        else:
            logger.info("Created git branch: %s", branch_name)

        state.git_branch = branch_name
        self.state_mgr._persist(state)
        return state

    async def _build_pom(self, state: RunState) -> RunState:
        """Invoke the POM Builder agent."""
        if state.pom_builder_attempts >= MAX_POM_BUILDER_ATTEMPTS:
            logger.error("Max POM Builder attempts reached")
            return self.state_mgr.transition(state, PipelineState.FAILED)

        state.pom_builder_attempts += 1

        self.reporter.on_state_change(
            state.state,
            PipelineState.BUILD_POM,
            {"attempt": state.pom_builder_attempts, "max_attempts": MAX_POM_BUILDER_ATTEMPTS},
        )
        self.reporter.on_agent_start(
            "pom_builder", POM_BUILDER_MODEL, POM_BUILDER_MAX_TURNS,
            state.pom_builder_attempts, MAX_POM_BUILDER_ATTEMPTS,
        )

        # Build test plan summary for the agent
        summary = _format_test_plan_summary(self.test_plan)

        # Build existing PO summary
        po_base = self.profile.resolve_path(self.profile.po_base_dir)
        existing_contracts = extract_contracts_from_dir(po_base, self.profile.project_root)
        existing_summary = contracts_to_json(existing_contracts) if existing_contracts else ""

        result = await self.pom_builder.run(
            test_plan_summary=summary,
            existing_po_summary=existing_summary,
            permission_mode=self.permission_mode,
        )


        self.reporter.on_agent_complete(
            "pom_builder", result.success, result.files_modified,
            result.cost_usd, result.turns,
        )

        state.record_invocation(AgentInvocation(
            agent_name="pom_builder",
            state=state.state,
            success=result.success,
            files_modified=result.files_modified,
            error=result.result_text if not result.success else "",
            result_text=result.result_text,
            cost_usd=result.cost_usd,
            turns=result.turns,
            tool_calls=result.tool_calls,
        ))

        if not result.success:
            # Check if the component directory was created despite the exit code 1.
            # The agent may have created files but run out of turns before finishing.
            # If any PO files now exist for the component, retry BUILD_POM so the
            # next attempt can pick up where it left off (it will see existing contracts).
            po_base = self.profile.resolve_path(self.profile.po_base_dir)
            any_po_created = any(
                _find_po_dir(po_base, comp) is not None
                for comp in self.test_plan.components
            )
            if any_po_created and state.pom_builder_attempts < MAX_POM_BUILDER_ATTEMPTS:
                logger.warning(
                    "POM Builder exited with error but PO files were created "
                    "(attempt %d/%d). Retrying to complete remaining work.",
                    state.pom_builder_attempts,
                    MAX_POM_BUILDER_ATTEMPTS,
                )
                return self.state_mgr.transition(state, PipelineState.BUILD_POM)
            return self.state_mgr.transition(state, PipelineState.FAILED)

        # Use the agent's declared output as primary source; fall back to tool-call tracking.
        declared = _parse_pipeline_output(result.result_text, "created_files")
        po_files = declared or result.files_modified
        logger.info("POM Builder reported %d file(s): %s", len(po_files), po_files)
        state.generated_po_files.extend(po_files)
        return self.state_mgr.transition(state, PipelineState.VALIDATE_POM)

    async def _validate_pom(self, state: RunState) -> RunState:
        """Run deterministic validation on generated PO files."""
        self.reporter.on_state_change(state.state, PipelineState.VALIDATE_POM)

        results = await run_all_checks(self.profile, state.generated_po_files)
        state.validation_results.extend(results)

        for r in results:
            self.reporter.on_validation_result(r)

        all_passed = all(r.passed for r in results)
        if not all_passed:
            failed = [r for r in results if not r.passed]
            logger.error("POM validation failed: %s", [r.check_name for r in failed])
            # POM validation failure is fatal — agent should have self-corrected
            return self.state_mgr.transition(state, PipelineState.FAILED)

        return self.state_mgr.transition(state, PipelineState.WRITE_TEST)

    async def _write_test(self, state: RunState) -> RunState:
        """Invoke the Test Writer agent."""
        if state.test_writer_attempts >= MAX_TEST_WRITER_ATTEMPTS:
            logger.error("Max Test Writer attempts reached")
            return self.state_mgr.transition(state, PipelineState.FAILED)

        state.test_writer_attempts += 1

        self.reporter.on_state_change(
            state.state,
            PipelineState.WRITE_TEST,
            {"attempt": state.test_writer_attempts, "max_attempts": MAX_TEST_WRITER_ATTEMPTS},
        )
        self.reporter.on_agent_start(
            "test_writer", TEST_WRITER_MODEL, TEST_WRITER_MAX_TURNS,
            state.test_writer_attempts, MAX_TEST_WRITER_ATTEMPTS,
        )

        # Get POM contracts for the test writer
        po_base = self.profile.resolve_path(self.profile.po_base_dir)
        contracts = extract_contracts_from_dir(po_base, self.profile.project_root)
        contracts_json = contracts_to_json(contracts)

        # Full test plan text
        plan_path = Path(self.test_plan.source_file)
        test_plan_text = plan_path.read_text(encoding="utf-8")

        # Snapshot existing spec files before running the agent so we can detect
        # newly created files regardless of whether the agent mentions them in output.
        project_root = self.profile.project_root
        test_dir = project_root / self.profile.test_dir
        existing_specs = _snapshot_spec_files(test_dir, project_root)

        result = await self.test_writer.run(
            test_plan_text=test_plan_text,
            pom_contracts_json=contracts_json,
            permission_mode=self.permission_mode,
        )


        self.reporter.on_agent_complete(
            "test_writer", result.success, result.files_modified,
            result.cost_usd, result.turns,
        )

        state.record_invocation(AgentInvocation(
            agent_name="test_writer",
            state=state.state,
            success=result.success,
            files_modified=result.files_modified,
            error=result.result_text if not result.success else "",
            result_text=result.result_text,
            cost_usd=result.cost_usd,
            turns=result.turns,
            tool_calls=result.tool_calls,
        ))

        if not result.success:
            return self.state_mgr.transition(state, PipelineState.FAILED)

        # Priority: agent-declared > filesystem diff > tool-call tracking.
        # Agent-declared is authoritative — the LLM explicitly reports what it created.
        # Filesystem diff catches files created via Bash but misses pre-existing files.
        # Tool-call tracking (result.files_modified) is the last resort.
        new_specs = _snapshot_spec_files(test_dir, project_root)
        diff_files = sorted(f for f in new_specs if f not in existing_specs)
        declared = _parse_pipeline_output(result.result_text, "created_files")
        detected_files = declared or diff_files or result.files_modified
        logger.info(
            "Test writer files — declared: %s, diff: %s, tool-tracked: %s → using: %s",
            declared, diff_files, result.files_modified, detected_files,
        )
        state.generated_test_files.extend(detected_files)

        return self.state_mgr.transition(state, PipelineState.VALIDATE_TEST)

    async def _validate_test(self, state: RunState) -> RunState:
        """Run deterministic validation on generated test files."""
        self.reporter.on_state_change(state.state, PipelineState.VALIDATE_TEST)

        results = await run_all_checks(self.profile, state.generated_test_files)
        state.validation_results.extend(results)

        for r in results:
            self.reporter.on_validation_result(r)

        all_passed = all(r.passed for r in results)
        if not all_passed:
            failed = [r for r in results if not r.passed]
            logger.error("Test validation failed: %s", [r.check_name for r in failed])
            # Retry via write_test (one retry)
            if state.test_writer_attempts < MAX_TEST_WRITER_ATTEMPTS:
                return self.state_mgr.transition(state, PipelineState.WRITE_TEST)
            return self.state_mgr.transition(state, PipelineState.FAILED)

        return self.state_mgr.transition(state, PipelineState.RUN_TEST)

    async def _run_test(self, state: RunState) -> RunState:
        """Execute generated tests with Playwright."""
        self.reporter.on_state_change(state.state, PipelineState.RUN_TEST)

        test_files = state.generated_test_files
        if not test_files:
            logger.error("No test files to run")
            return self.state_mgr.transition(state, PipelineState.FAILED)

        files_arg = " ".join(f'"{f}"' for f in test_files)
        cmd = f"npx playwright test {files_arg} --reporter=json"

        proc = await asyncio.create_subprocess_shell(
            cmd,
            cwd=str(self.profile.project_root),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)

        stdout_text = (stdout or b"").decode("utf-8", errors="replace")
        stderr_text = (stderr or b"").decode("utf-8", errors="replace")

        # Parse JSON report
        json_report = None
        try:
            json_report = json.loads(stdout_text)
        except (json.JSONDecodeError, ValueError):
            pass

        passed = proc.returncode == 0

        # Extract human-readable error text from the JSON report when available.
        # Playwright writes failure details to stdout (JSON), not stderr, so we
        # must pull them from the report for the classifier to work correctly.
        error_text = ""
        if not passed:
            if json_report:
                error_text = _extract_errors_from_json_report(json_report)
            # Fall back to stderr if the JSON report had no useful messages
            if not error_text:
                error_text = stderr_text

        test_result = TestResult(
            passed=passed,
            error_output=error_text,
            json_report=json_report,
        )

        if json_report and "stats" in json_report:
            stats = json_report["stats"]
            test_result.total = stats.get("expected", 0) + stats.get("unexpected", 0)
            test_result.failed_count = stats.get("unexpected", 0)

        state.test_results.append(test_result)

        self.reporter.on_test_run(
            test_files, passed, test_result.failed_count, error_text,
        )

        if passed:
            logger.info("All tests passed!")
            return self.state_mgr.transition(state, PipelineState.DONE)

        logger.warning("Tests failed (%d failures)", test_result.failed_count)
        return self.state_mgr.transition(state, PipelineState.CLASSIFY_FAILURE)

    async def _classify_failure(self, state: RunState) -> RunState:
        """Classify the test failure and decide routing."""
        self.reporter.on_state_change(state.state, PipelineState.CLASSIFY_FAILURE)

        if not state.test_results:
            return self.state_mgr.transition(state, PipelineState.FAILED)

        last_result = state.test_results[-1]
        classified = classify_failure(last_result.error_output)

        failure = FailureRecord(
            category=classified.category,
            message=classified.message,
            file_paths=classified.file_paths,
            routed_to=classified.route_to,
        )

        self.reporter.on_failure_classified(
            classified.category, classified.route_to, classified.message,
        )

        # Check for repeated identical failure
        if state.has_repeated_failure(classified.category, classified.message):
            logger.error("Repeated failure detected: %s — aborting", classified.category)
            state.record_failure(failure)
            return self.state_mgr.transition(state, PipelineState.FAILED)

        state.record_failure(failure)

        match classified.route_to:
            case "healer":
                return self.state_mgr.transition(state, PipelineState.HEAL)
            case "pom_builder":
                return self.state_mgr.transition(state, PipelineState.BUILD_POM)
            case "abort" | _:
                return self.state_mgr.transition(state, PipelineState.FAILED)

    async def _heal(self, state: RunState) -> RunState:
        """Invoke the Healer agent to patch failing tests/POs."""
        if state.healer_attempts >= MAX_HEALER_ATTEMPTS:
            logger.error("Max Healer attempts reached")
            return self.state_mgr.transition(state, PipelineState.FAILED)

        state.healer_attempts += 1

        self.reporter.on_state_change(
            state.state,
            PipelineState.HEAL,
            {"attempt": state.healer_attempts, "max_attempts": MAX_HEALER_ATTEMPTS},
        )
        self.reporter.on_agent_start(
            "healer", HEALER_MODEL, HEALER_MAX_TURNS,
            state.healer_attempts, MAX_HEALER_ATTEMPTS,
        )

        last_failure = state.failure_history[-1] if state.failure_history else None
        if not last_failure:
            return self.state_mgr.transition(state, PipelineState.FAILED)

        last_test = state.test_results[-1] if state.test_results else None
        error_output = last_test.error_output if last_test else last_failure.message

        result = await self.healer.run(
            error_output=error_output,
            failure_category=last_failure.category,
            relevant_files=last_failure.file_paths,
            permission_mode=self.permission_mode,
        )


        self.reporter.on_agent_complete(
            "healer", result.success, result.files_modified,
            result.cost_usd, result.turns,
        )

        state.record_invocation(AgentInvocation(
            agent_name="healer",
            state=state.state,
            success=result.success,
            files_modified=result.files_modified,
            error=result.result_text if not result.success else "",
            result_text=result.result_text,
            cost_usd=result.cost_usd,
            turns=result.turns,
            tool_calls=result.tool_calls,
        ))

        if not result.success:
            return self.state_mgr.transition(state, PipelineState.FAILED)

        # After healing, validate then re-run tests
        heal_files = state.generated_po_files + state.generated_test_files
        results = await run_all_checks(self.profile, heal_files)
        state.validation_results.extend(results)

        for r in results:
            self.reporter.on_validation_result(r)

        if not all(r.passed for r in results):
            return self.state_mgr.transition(state, PipelineState.FAILED)

        return self.state_mgr.transition(state, PipelineState.RUN_TEST)


def _parse_pipeline_output(result_text: str, key: str) -> list[str]:
    """Extract a list from the agent's pipeline_output JSON block.

    Agents are instructed to end their output with:
        ```json
        {"pipeline_output": {"created_files": [...]}}
        ```
    This is the authoritative source for files produced by each phase.
    Returns an empty list if the block is absent or malformed.
    """
    match = re.search(
        r'```json\s*(\{[^`]*?"pipeline_output"[^`]*?\})\s*```',
        result_text,
        re.DOTALL,
    )
    if not match:
        return []
    try:
        data = json.loads(match.group(1))
        value = data.get("pipeline_output", {}).get(key, [])
        return value if isinstance(value, list) else []
    except (json.JSONDecodeError, AttributeError):
        return []


def _recover_generated_files(state: RunState) -> RunState:
    """Re-populate empty generated-file lists from stored agent invocation records.

    Called when resuming a failed run — ensures downstream phases have the file
    lists they need even if the original run failed to populate them (e.g. due
    to the snapshot-diff mechanism missing pre-existing files).
    """
    if not state.generated_test_files:
        for inv in state.agent_invocations:
            if inv.agent_name == "test_writer" and inv.success and inv.result_text:
                recovered = _parse_pipeline_output(inv.result_text, "created_files")
                if recovered:
                    state.generated_test_files = recovered
                    logger.info(
                        "Resume: recovered %d test file(s) from stored invocation",
                        len(recovered),
                    )
                    break

    if not state.generated_po_files:
        for inv in state.agent_invocations:
            if inv.agent_name == "pom_builder" and inv.success and inv.result_text:
                recovered = _parse_pipeline_output(inv.result_text, "created_files")
                if recovered:
                    state.generated_po_files = recovered
                    logger.info(
                        "Resume: recovered %d PO file(s) from stored invocation",
                        len(recovered),
                    )
                    break

    return state


def _normalize_name(name: str) -> str:
    """Strip hyphens and underscores, lowercase — used for fuzzy directory matching."""
    return name.replace("-", "").replace("_", "").lower()


def _find_po_dir(po_base: Path, component: str) -> Path | None:
    """Return the PO directory for *component*, or None if no match exists.

    Tries an exact name match first, then falls back to a normalized comparison
    (strips hyphens and underscores, case-insensitive) against all subdirectories
    of *po_base*.  The first normalized match wins.
    """
    exact = po_base / component
    if exact.is_dir():
        return exact

    if not po_base.is_dir():
        return None

    target = _normalize_name(component)
    for candidate in po_base.iterdir():
        if candidate.is_dir() and _normalize_name(candidate.name) == target:
            return candidate

    return None


def _snapshot_spec_files(test_dir: Path, project_root: Path) -> set[str]:
    """Return relative paths (from project_root) of all .spec.ts files under test_dir."""
    if not test_dir.is_dir():
        return set()
    return {
        str(p.relative_to(project_root)).replace("\\", "/")
        for p in test_dir.rglob("*.spec.ts")
    }


def _extract_errors_from_json_report(report: dict) -> str:
    """Walk a Playwright JSON report and collect error messages from failed tests."""
    messages: list[str] = []

    def _walk_suites(suites: list[dict]) -> None:
        for suite in suites:
            _walk_suites(suite.get("suites", []))
            for spec in suite.get("specs", []):
                for test in spec.get("tests", []):
                    for result in test.get("results", []):
                        err = result.get("error") or {}
                        msg = err.get("message", "")
                        if msg and msg not in messages:
                            messages.append(msg)
                        # Also check step-level errors
                        for step in result.get("steps", []):
                            serr = step.get("error") or {}
                            smsg = serr.get("message", "")
                            if smsg and smsg not in messages:
                                messages.append(smsg)

    _walk_suites(report.get("suites", []))
    return "\n".join(messages[:10])  # Limit to first 10 unique errors


def _format_test_plan_summary(test_plan) -> str:
    """Format test plan scenarios into a readable summary for agents."""
    lines: list[str] = []
    for s in test_plan.scenarios:
        lines.append(f"## {s.id}: {s.scenario_name}")
        lines.append(f"Suite: {s.suite} | Feature: {s.feature} | Component: {s.component}")
        if s.variables:
            lines.append(f"Variables: {s.variables}")
        if s.setup:
            lines.append(f"Setup: {s.setup}")
        if s.background:
            lines.append(f"Background:\n{s.background}")
        for step in s.steps:
            lines.append(f"  {step}")
        lines.append("")
    return "\n".join(lines)
