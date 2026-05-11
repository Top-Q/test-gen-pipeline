"""Pipeline reporter — event callbacks for real-time progress display."""

from __future__ import annotations

import sys
from typing import Any, Protocol

from .schemas.run_state import ValidationResult


class PipelineReporter(Protocol):
    """Protocol for pipeline progress reporting.

    Implementations receive callbacks at key pipeline moments and render
    output however they choose (rich console, plain text, silent, etc.).
    """

    def on_pipeline_start(
        self,
        run_id: str,
        profile_name: str,
        plan_path: str,
        scenarios_count: int,
        components: set[str],
    ) -> None: ...

    def on_state_change(
        self, from_state: str, to_state: str, context: dict[str, Any] | None = None
    ) -> None: ...

    def on_agent_start(
        self,
        agent_name: str,
        model: str,
        max_turns: int,
        attempt: int,
        max_attempts: int,
    ) -> None: ...

    def on_agent_tool_use(
        self, agent_name: str, tool_name: str, tool_input: dict[str, Any]
    ) -> None: ...

    def on_agent_tool_result(
        self, agent_name: str, tool_name: str, content: str, is_error: bool
    ) -> None: ...

    def on_agent_text(self, agent_name: str, text: str) -> None: ...

    def on_agent_thinking(self, agent_name: str, summary: str) -> None: ...

    def on_agent_complete(
        self,
        agent_name: str,
        success: bool,
        files_modified: list[str],
        cost_usd: float,
        turns: int,
    ) -> None: ...

    def on_validation_start(self, check_name: str) -> None: ...

    def on_validation_result(self, result: ValidationResult) -> None: ...

    def on_test_run(
        self,
        files: list[str],
        passed: bool,
        failed_count: int,
        error_output: str,
    ) -> None: ...

    def on_preflight_check(
        self, check_name: str, passed: bool, detail: str
    ) -> None: ...

    def on_failure_classified(
        self, category: str, routed_to: str, message: str
    ) -> None: ...

    def on_pipeline_complete(
        self, final_state: str, run_id: str, total_cost: float
    ) -> None: ...


class QuietReporter:
    """No-op reporter — all callbacks silently do nothing."""

    def on_pipeline_start(self, run_id, profile_name, plan_path, scenarios_count, components):
        pass

    def on_state_change(self, from_state, to_state, context=None):
        pass

    def on_agent_start(self, agent_name, model, max_turns, attempt, max_attempts):
        pass

    def on_agent_tool_use(self, agent_name, tool_name, tool_input):
        pass

    def on_agent_tool_result(self, agent_name, tool_name, content, is_error):
        pass

    def on_agent_text(self, agent_name, text):
        pass

    def on_agent_thinking(self, agent_name, summary):
        pass

    def on_agent_complete(self, agent_name, success, files_modified, cost_usd, turns):
        pass

    def on_validation_start(self, check_name):
        pass

    def on_validation_result(self, result):
        pass

    def on_test_run(self, files, passed, failed_count, error_output):
        pass

    def on_preflight_check(self, check_name, passed, detail):
        pass

    def on_failure_classified(self, category, routed_to, message):
        pass

    def on_pipeline_complete(self, final_state, run_id, total_cost):
        pass


def _truncate(text: str, max_len: int = 120) -> str:
    """Truncate text with ellipsis if it exceeds max_len."""
    if len(text) <= max_len:
        return text
    return text[: max_len - 3] + "..."


def _tool_summary(tool_name: str, tool_input: dict[str, Any]) -> str:
    """Extract the most relevant info from a tool call for display."""
    # File-oriented tools: show the path
    for key in ("file_path", "path", "filename"):
        if key in tool_input:
            return str(tool_input[key])

    # Bash: show the command
    if "command" in tool_input:
        return _truncate(str(tool_input["command"]), 80)

    # Grep/search: show the pattern
    if "pattern" in tool_input:
        path = tool_input.get("path", "")
        pat = tool_input["pattern"]
        return f"{pat}" + (f"  ({path})" if path else "")

    # Glob
    if "glob" in tool_input:
        return str(tool_input["glob"])

    # Fallback: first string value
    for v in tool_input.values():
        if isinstance(v, str) and v:
            return _truncate(v, 80)

    return ""


class RichConsoleReporter:
    """Rich-based reporter rendering Claude Code-style output to stderr.

    Degrades gracefully when rich is unavailable or the terminal is dumb.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._console = None
        self._total_cost = 0.0
        self._turn_count = 0
        try:
            from rich.console import Console

            self._console = Console(stderr=True, highlight=False)
        except ImportError:
            pass

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _print(self, *args, **kwargs) -> None:
        if self._console:
            self._console.print(*args, **kwargs)
        else:
            print(*args, file=sys.stderr, **kwargs)

    def _rule(self, title: str) -> None:
        if self._console:
            from rich.rule import Rule

            self._console.print(Rule(title, style="bold cyan", align="left"))
        else:
            print(f"\n-- {title} {'─' * max(0, 60 - len(title))}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Pipeline lifecycle
    # ------------------------------------------------------------------

    def on_pipeline_start(
        self, run_id, profile_name, plan_path, scenarios_count, components
    ):
        comps = ", ".join(sorted(components))
        if self._console:
            from rich.panel import Panel

            body = (
                f"Profile: [bold]{profile_name}[/bold] | "
                f"{scenarios_count} scenario(s) | "
                f"Components: [bold]{comps}[/bold]"
            )
            self._console.print(
                Panel(
                    body,
                    title=f"[bold]Pipeline Run: {run_id}[/bold]",
                    border_style="cyan",
                )
            )
        else:
            print(
                f"\n=== Pipeline Run: {run_id} ===\n"
                f"Profile: {profile_name} | {scenarios_count} scenario(s) | "
                f"Components: {comps}\n",
                file=sys.stderr,
            )

    def on_state_change(self, from_state, to_state, context=None):
        extra = ""
        if context:
            parts = []
            if "attempt" in context and "max_attempts" in context:
                parts.append(f"attempt {context['attempt']}/{context['max_attempts']}")
            if "info" in context:
                parts.append(str(context["info"]))
            if parts:
                extra = f" ({', '.join(parts)})"
        self._rule(f"{to_state}{extra}")

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def on_agent_start(self, agent_name, model, max_turns, attempt, max_attempts):
        self._turn_count = 0
        model_short = model.split("/")[-1] if "/" in model else model
        self._print(
            f"  Agent: [bold]{agent_name}[/bold] | {model_short} | "
            f"max {max_turns} turns"
            if self._console
            else f"  Agent: {agent_name} | {model_short} | max {max_turns} turns",
        )
        self._print()

    def on_agent_tool_use(self, agent_name, tool_name, tool_input):
        self._turn_count += 1
        summary = _tool_summary(tool_name, tool_input)
        display_name = tool_name.ljust(6)
        if self._console:
            self._print(
                f"  [dim bold]\\[gear][/dim bold] [yellow]{display_name}[/yellow] [dim]{summary}[/dim]"
            )
        else:
            print(f"  * {display_name} {summary}", file=sys.stderr)

    def on_agent_tool_result(self, agent_name, tool_name, content, is_error):
        if is_error:
            snippet = _truncate(content, 120)
            if self._console:
                self._print(f"    [red]ERROR: {snippet}[/red]")
            else:
                print(f"    ERROR: {snippet}", file=sys.stderr)

    def on_agent_text(self, agent_name, text):
        if not self.verbose:
            return
        # Show a short excerpt of agent reasoning
        first_line = text.strip().split("\n")[0]
        excerpt = _truncate(first_line, 100)
        if excerpt:
            if self._console:
                self._print(f"    [dim italic]{excerpt}[/dim italic]")
            else:
                print(f"    > {excerpt}", file=sys.stderr)

    def on_agent_thinking(self, agent_name, summary):
        if not self.verbose:
            return
        # Show first sentence only
        first_sentence = summary.split(".")[0].strip()
        if first_sentence:
            excerpt = _truncate(first_sentence, 100)
            if self._console:
                self._print(f"    [dim]{excerpt}[/dim]")
            else:
                print(f"    (thinking) {excerpt}", file=sys.stderr)

    def on_agent_complete(self, agent_name, success, files_modified, cost_usd, turns):
        self._total_cost += cost_usd
        self._print()
        if success:
            if self._console:
                self._print(
                    f"  [green bold]\\[check][/green bold] {agent_name} completed "
                    f"({turns} turn(s), ${cost_usd:.2f})"
                )
            else:
                print(
                    f"  OK {agent_name} completed ({turns} turn(s), ${cost_usd:.2f})",
                    file=sys.stderr,
                )
        else:
            if self._console:
                self._print(
                    f"  [red bold]\\[cross][/red bold] {agent_name} failed "
                    f"({turns} turn(s), ${cost_usd:.2f})"
                )
            else:
                print(
                    f"  FAIL {agent_name} failed ({turns} turn(s), ${cost_usd:.2f})",
                    file=sys.stderr,
                )

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def on_preflight_check(self, check_name, passed, detail):
        detail_short = _truncate(detail, 80)
        if passed:
            if self._console:
                self._print(f"  [green]\\[check][/green] {check_name}: {detail_short}")
            else:
                print(f"  OK {check_name}: {detail_short}", file=sys.stderr)
        else:
            if self._console:
                self._print(f"  [red]\\[cross][/red] {check_name}: {detail_short}")
            else:
                print(f"  FAIL {check_name}: {detail_short}", file=sys.stderr)

    def on_validation_start(self, check_name):
        pass  # We report on result instead

    def on_validation_result(self, result):
        if result.passed:
            files_info = f" ({len(result.files_checked)} file(s))" if result.files_checked else ""
            if self._console:
                self._print(f"  [green]\\[check][/green] {result.check_name}{files_info}")
            else:
                print(f"  PASS {result.check_name}{files_info}", file=sys.stderr)
        else:
            if self._console:
                self._print(f"  [red]\\[cross][/red] {result.check_name}")
                # Show first few lines of output
                for line in result.output.split("\n")[:3]:
                    self._print(f"    [dim]{_truncate(line, 100)}[/dim]")
            else:
                print(f"  FAIL {result.check_name}", file=sys.stderr)
                for line in result.output.split("\n")[:3]:
                    print(f"    {_truncate(line, 100)}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Test execution
    # ------------------------------------------------------------------

    def on_test_run(self, files, passed, failed_count, error_output):
        file_count = len(files)
        if passed:
            if self._console:
                self._print(
                    f"  [green bold]\\[check][/green bold] All tests passed ({file_count} file(s))"
                )
            else:
                print(f"  OK All tests passed ({file_count} file(s))", file=sys.stderr)
        else:
            if self._console:
                self._print(
                    f"  [red bold]\\[cross][/red bold] {failed_count} test(s) failed"
                )
                # Show error excerpt
                for line in error_output.split("\n")[:5]:
                    trimmed = _truncate(line.strip(), 120)
                    if trimmed:
                        self._print(f"    [dim]{trimmed}[/dim]")
            else:
                print(f"  FAIL {failed_count} test(s) failed", file=sys.stderr)
                for line in error_output.split("\n")[:5]:
                    trimmed = _truncate(line.strip(), 120)
                    if trimmed:
                        print(f"    {trimmed}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Failure classification
    # ------------------------------------------------------------------

    def on_failure_classified(self, category, routed_to, message):
        msg_short = _truncate(message, 80)
        if self._console:
            self._print(
                f"  [yellow]Category:[/yellow] {category} "
                f"[yellow]-> [/yellow]{routed_to}"
            )
            if msg_short:
                self._print(f"    [dim]{msg_short}[/dim]")
        else:
            print(f"  Category: {category} -> {routed_to}", file=sys.stderr)
            if msg_short:
                print(f"    {msg_short}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Pipeline complete
    # ------------------------------------------------------------------

    def on_pipeline_complete(self, final_state, run_id, total_cost):
        state_style = "green" if final_state == "done" else "red"
        if self._console:
            from rich.panel import Panel

            body = (
                f"State: [{state_style} bold]{final_state}[/{state_style} bold] | "
                f"Cost: ${total_cost:.2f}"
            )
            self._console.print(
                Panel(body, title="[bold]Pipeline Complete[/bold]", border_style="cyan")
            )
        else:
            print(
                f"\n=== Pipeline Complete ===\n"
                f"State: {final_state} | Cost: ${total_cost:.2f}\n",
                file=sys.stderr,
            )
