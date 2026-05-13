"""Pipeline reporter — event callbacks for real-time progress display."""

from __future__ import annotations

import sys
from pathlib import Path
from typing import Any, Protocol

from .schemas.run_state import ValidationResult

# ---------------------------------------------------------------------------
# Color mappings
# ---------------------------------------------------------------------------

# Tool type → Rich color
_TOOL_COLORS: dict[str, str] = {
    "Read": "blue",
    "Write": "green",
    "Edit": "yellow",
    "Bash": "magenta",
    "Grep": "cyan",
    "Glob": "cyan",
    "NotebookEdit": "yellow",
    "WebFetch": "blue",
    "WebSearch": "blue",
    "Task": "bright_black",
}

# Pipeline state → Rich color
_STATE_COLORS: dict[str, str] = {
    "preflight": "bright_black",
    "analyze_plan": "cyan",
    "check_pom": "cyan",
    "investigate_dom": "cyan",
    "build_pom": "blue",
    "validate_pom": "yellow",
    "write_test": "blue",
    "validate_test": "yellow",
    "run_test": "magenta",
    "classify_failure": "dark_orange3",
    "heal": "dark_orange3",
    "done": "green",
    "failed": "red",
}

# Agent name → Rich color
_AGENT_COLORS: dict[str, str] = {
    "pom_builder": "blue",
    "test_writer": "green",
    "healer": "dark_orange3",
    "investigator": "cyan",
}


def _tool_color(tool_name: str) -> str:
    return _TOOL_COLORS.get(tool_name, "white")


def _state_color(state: str) -> str:
    return _STATE_COLORS.get(state, "cyan")


def _agent_color(agent_name: str) -> str:
    return _AGENT_COLORS.get(agent_name, "white")


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


def _short_model(model: str) -> str:
    """Shorten a model ID for display, e.g. 'claude-sonnet-4-20250514' → 'sonnet-4'."""
    name = model.split("/")[-1]  # strip any org prefix
    name = name.replace("claude-", "")
    # Drop trailing date suffix like -20250514
    import re
    name = re.sub(r"-\d{8}$", "", name)
    return name


class RichConsoleReporter:
    """Rich-based reporter with color-coded tool calls, thinking, and state display.

    Degrades gracefully when rich is unavailable or the terminal is dumb.
    """

    def __init__(self, verbose: bool = False):
        self.verbose = verbose
        self._console = None
        self._total_cost = 0.0
        self._turn_count = 0
        self._current_agent = ""
        self._current_state = ""
        import logging
        logger = logging.getLogger(__name__)
        try:
            from rich.console import Console
            # Windows Terminal supports colors with force_terminal=True
            self._console = Console(
                stderr=True,
                highlight=False,
                force_terminal=True,
                no_color=False,  # Explicitly enable colors
            )
            logger.debug("Rich console initialized successfully")
        except Exception as e:
            logger.warning("Failed to initialize Rich console: %s. Falling back to plain text.", e)
            self._console = None

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _print(self, markup: str, **kwargs) -> None:
        """Print Rich markup to stderr, with plain-text fallback."""
        if self._console:
            self._console.print(markup, **kwargs)
        else:
            import re
            plain = re.sub(r"\[/?[^\]]*\]", "", markup)
            print(plain, file=sys.stderr, **{k: v for k, v in kwargs.items() if k in ("end", "sep")})

    def _rule(self, title: str, style: str = "bold cyan") -> None:
        if self._console:
            from rich.rule import Rule
            self._console.print(Rule(title, style=style, align="left"))
        else:
            plain_title = title  # already plain text in non-rich path
            print(f"\n-- {plain_title} {'─' * max(0, 60 - len(plain_title))}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Pipeline lifecycle
    # ------------------------------------------------------------------

    def on_pipeline_start(self, run_id, profile_name, plan_path, scenarios_count, components):
        comps = ", ".join(sorted(components))
        if self._console:
            from rich.panel import Panel
            body = (
                f"[bold]{profile_name}[/bold]  "
                f"[dim]{scenarios_count} scenario(s)[/dim]  "
                f"components: [bold cyan]{comps}[/bold cyan]"
            )
            self._console.print(Panel(
                body,
                title=f"[bold]Pipeline  {run_id}[/bold]",
                border_style="cyan",
                padding=(0, 1),
            ))
        else:
            print(
                f"\n=== Pipeline Run: {run_id} ===\n"
                f"Profile: {profile_name} | {scenarios_count} scenario(s) | Components: {comps}\n",
                file=sys.stderr,
            )

    def on_state_change(self, from_state, to_state, context=None):
        self._current_state = to_state
        extra_parts: list[str] = []
        if context:
            if "attempt" in context and "max_attempts" in context:
                extra_parts.append(f"attempt {context['attempt']}/{context['max_attempts']}")
            if "info" in context:
                extra_parts.append(str(context["info"]))
        extra = f"  ({', '.join(extra_parts)})" if extra_parts else ""

        color = _state_color(to_state)
        label = to_state.upper().replace("_", " ")

        if self._console:
            from rich.rule import Rule
            title = f"[bold {color}]{label}[/bold {color}][dim]{extra}[/dim]"
            self._console.print(Rule(title, style=color, align="left"))
        else:
            print(f"\n-- {label}{extra} {'─' * max(0, 55 - len(label))}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Agent lifecycle
    # ------------------------------------------------------------------

    def on_agent_start(self, agent_name, model, max_turns, attempt, max_attempts):
        self._turn_count = 0
        self._current_agent = agent_name
        color = _agent_color(agent_name)
        model_display = _short_model(model)
        attempt_str = (
            f"  [dim](attempt {attempt}/{max_attempts})[/dim]" if max_attempts > 1 else ""
        )
        if self._console:
            self._print(
                f"\n  [bold {color}]◆ {agent_name}[/bold {color}]"
                f"  [dim]{model_display}  ·  max {max_turns} turns[/dim]"
                f"{attempt_str}"
            )
        else:
            atxt = f" (attempt {attempt}/{max_attempts})" if max_attempts > 1 else ""
            print(f"\n  Agent: {agent_name} | {model_display} | max {max_turns} turns{atxt}", file=sys.stderr)

    def on_agent_tool_use(self, agent_name, tool_name, tool_input):
        self._turn_count += 1
        summary = _tool_summary(tool_name, tool_input)
        color = _tool_color(tool_name)
        if self._console:
            turn = f"[dim]#{self._turn_count:>2}[/dim]"
            tool = f"[{color} bold]{tool_name:<8}[/{color} bold]"
            detail = f"[dim]{summary}[/dim]" if summary else ""
            self._print(f"  {turn}  {tool}  {detail}")
        else:
            print(f"  #{self._turn_count:>2}  {tool_name:<8}  {summary}", file=sys.stderr)

    def on_agent_tool_result(self, agent_name, tool_name, content, is_error):
        if is_error:
            snippet = _truncate(content, 120)
            if self._console:
                self._print(f"          [red]✗ {snippet}[/red]")
            else:
                print(f"          ERROR: {snippet}", file=sys.stderr)

    def on_agent_text(self, agent_name, text):
        stripped = text.strip()
        if not stripped:
            return
        if self.verbose:
            # Verbose: show all lines
            if self._console:
                for line in stripped.splitlines():
                    if line.strip():
                        self._print(f"     [dim italic]{line}[/dim italic]")
            else:
                for line in stripped.splitlines():
                    if line.strip():
                        print(f"     {line}", file=sys.stderr)
        else:
            # Normal: show first meaningful line only, truncated
            first_line = next((l for l in stripped.splitlines() if l.strip()), "")
            if len(first_line) < 20:
                return
            if self._console:
                self._print(f"     [dim italic]{_truncate(first_line, 100)}[/dim italic]")
            else:
                print(f"     {_truncate(first_line, 100)}", file=sys.stderr)

    def on_agent_thinking(self, agent_name, summary):
        # Always show thinking excerpts — bright magenta for visibility
        first_sentence = summary.split(".")[0].strip()
        if not first_sentence:
            return
        excerpt = _truncate(first_sentence, 100)
        if self._console:
            self._print(f"     [bright_magenta]~ {excerpt}[/bright_magenta]")
        else:
            print(f"     ~ (thinking) {excerpt}", file=sys.stderr)

    def on_agent_complete(self, agent_name, success, files_modified, cost_usd, turns):
        self._total_cost += cost_usd
        color = _agent_color(agent_name)
        stats = f"{turns} turn(s)  ·  ${cost_usd:.2f}"

        if self._console:
            if success:
                self._print(
                    f"\n  [green bold]✓[/green bold] [{color}]{agent_name}[/{color}]"
                    f"  [dim]{stats}[/dim]"
                )
            else:
                self._print(
                    f"\n  [red bold]✗[/red bold] [{color}]{agent_name}[/{color}]"
                    f"  [dim]{stats}[/dim]"
                )
            if files_modified:
                names = [Path(f).name for f in files_modified[:6]]
                files_str = ", ".join(names)
                if len(files_modified) > 6:
                    files_str += f"  +{len(files_modified) - 6} more"
                self._print(f"    [dim]files: {files_str}[/dim]")
        else:
            status = "OK" if success else "FAIL"
            print(f"\n  {status} {agent_name}  ({stats})", file=sys.stderr)
            if files_modified:
                names = [Path(f).name for f in files_modified[:6]]
                print(f"    files: {', '.join(names)}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Validation
    # ------------------------------------------------------------------

    def on_preflight_check(self, check_name, passed, detail):
        detail_short = _truncate(detail, 80)
        if self._console:
            icon = "[green]✓[/green]" if passed else "[red]✗[/red]"
            self._print(f"  {icon}  {check_name}: [dim]{detail_short}[/dim]")
        else:
            status = "OK  " if passed else "FAIL"
            print(f"  {status}  {check_name}: {detail_short}", file=sys.stderr)

    def on_validation_start(self, check_name):
        pass  # Report on result instead

    def on_validation_result(self, result):
        files_info = f"  [dim]({len(result.files_checked)} file(s))[/dim]" if result.files_checked else ""
        if result.passed:
            if self._console:
                self._print(f"  [green]✓[/green]  {result.check_name}{files_info}")
            else:
                count = f" ({len(result.files_checked)} file(s))" if result.files_checked else ""
                print(f"  PASS  {result.check_name}{count}", file=sys.stderr)
        else:
            if self._console:
                self._print(f"  [red]✗[/red]  [bold]{result.check_name}[/bold]")
                for line in result.output.split("\n")[:4]:
                    stripped = line.strip()
                    if stripped:
                        self._print(f"       [dim]{_truncate(stripped, 100)}[/dim]")
            else:
                print(f"  FAIL  {result.check_name}", file=sys.stderr)
                for line in result.output.split("\n")[:4]:
                    stripped = line.strip()
                    if stripped:
                        print(f"       {_truncate(stripped, 100)}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Test execution
    # ------------------------------------------------------------------

    def on_test_run(self, files, passed, failed_count, error_output):
        file_count = len(files)
        if self._console:
            if passed:
                self._print(
                    f"  [green bold]✓[/green bold]  All tests passed  [dim]({file_count} file(s))[/dim]"
                )
            else:
                self._print(
                    f"  [red bold]✗[/red bold]  [bold]{failed_count} test(s) failed[/bold]"
                )
                for line in error_output.split("\n")[:6]:
                    trimmed = _truncate(line.strip(), 120)
                    if trimmed:
                        self._print(f"       [dim]{trimmed}[/dim]")
        else:
            if passed:
                print(f"  OK    All tests passed ({file_count} file(s))", file=sys.stderr)
            else:
                print(f"  FAIL  {failed_count} test(s) failed", file=sys.stderr)
                for line in error_output.split("\n")[:6]:
                    trimmed = _truncate(line.strip(), 120)
                    if trimmed:
                        print(f"       {trimmed}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Failure classification
    # ------------------------------------------------------------------

    def on_failure_classified(self, category, routed_to, message):
        msg_short = _truncate(message, 90)
        if self._console:
            self._print(
                f"  [dark_orange3 bold]![/dark_orange3 bold]  "
                f"[dark_orange3]{category}[/dark_orange3]"
                f"  [dim]→[/dim]  [bold]{routed_to}[/bold]"
            )
            if msg_short:
                self._print(f"       [dim]{msg_short}[/dim]")
        else:
            print(f"  !  {category}  →  {routed_to}", file=sys.stderr)
            if msg_short:
                print(f"       {msg_short}", file=sys.stderr)

    # ------------------------------------------------------------------
    # Pipeline complete
    # ------------------------------------------------------------------

    def on_pipeline_complete(self, final_state, run_id, total_cost):
        state_style = "green" if final_state == "done" else "red"
        if self._console:
            from rich.panel import Panel
            body = (
                f"[{state_style} bold]{final_state.upper()}[/{state_style} bold]"
                f"  [dim]·[/dim]  "
                f"total cost: [bold]${total_cost:.2f}[/bold]"
            )
            self._console.print(Panel(
                body,
                title="[bold]Pipeline Complete[/bold]",
                border_style=state_style,
                padding=(0, 1),
            ))
        else:
            print(
                f"\n=== Pipeline Complete ===\n"
                f"State: {final_state} | Cost: ${total_cost:.2f}\n",
                file=sys.stderr,
            )
