"""Base agent runner wrapping the Claude Agent SDK."""

from __future__ import annotations

import logging
import os
import platform
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING, Generator

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import (
    AssistantMessage,
    ResultMessage,
    TextBlock,
    ThinkingBlock,
    ToolResultBlock,
    ToolUseBlock,
)

if TYPE_CHECKING:
    from ..reporter import PipelineReporter

logger = logging.getLogger(__name__)

# Windows CreateProcess has a ~32767 char command-line limit.
# When the system prompt exceeds this threshold, write it to a temp file
# and use --system-prompt-file instead to avoid WinError 206.
_WINDOWS_CMDLINE_SAFE_THRESHOLD = 8000


@contextmanager
def _system_prompt_option(system_prompt: str) -> Generator[str | dict, None, None]:
    """Yield a ClaudeAgentOptions-compatible system_prompt value.

    On Windows, if the prompt string is long enough to risk hitting the
    32767-char CreateProcess limit, it is written to a temporary file and
    the dict ``{"type": "file", "path": <tmpfile>}`` is yielded instead.
    The temp file is deleted on exit regardless of outcome.
    """
    if platform.system() == "Windows" and len(system_prompt) > _WINDOWS_CMDLINE_SAFE_THRESHOLD:
        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".txt", delete=False, encoding="utf-8"
        ) as tmp:
            tmp.write(system_prompt)
            tmp_path = tmp.name
        logger.debug(
            "System prompt is %d chars; writing to temp file to avoid WinError 206: %s",
            len(system_prompt),
            tmp_path,
        )
        try:
            yield {"type": "file", "path": tmp_path}
        finally:
            Path(tmp_path).unlink(missing_ok=True)
    else:
        yield system_prompt


@dataclass
class AgentResult:
    """Result of a single agent invocation."""

    agent_name: str
    success: bool
    result_text: str
    files_modified: list[str] = field(default_factory=list)
    cost_usd: float = 0.0
    turns: int = 0
    tool_calls: list[str] = field(default_factory=list)


class AgentRunner:
    """Wrapper around claude_agent_sdk.query() for pipeline agents."""

    def __init__(self, cwd: str | Path, reporter: PipelineReporter | None = None):
        self.cwd = str(cwd)
        self._reporter = reporter

    async def invoke(
        self,
        agent_name: str,
        prompt: str,
        system_prompt: str,
        tools: list[str],
        model: str,
        max_turns: int = 10,
        permission_mode: str = "bypassPermissions",
    ) -> AgentResult:
        """Invoke a Claude agent and collect the result."""
        logger.info("Invoking agent %s (model=%s, max_turns=%d)", agent_name, model, max_turns)

        result_text = ""
        cost_usd = 0.0
        turns = 0
        files_modified: list[str] = []
        tool_calls: list[str] = []
        reporter = self._reporter

        with _system_prompt_option(system_prompt) as sp_option:
            options = ClaudeAgentOptions(
                system_prompt=sp_option,
                cwd=self.cwd,
                allowed_tools=tools,
                permission_mode=permission_mode,
                max_turns=max_turns,
                model=model,
            )

            claudecode_val = os.environ.pop("CLAUDECODE", None)
            try:
                async for message in query(prompt=prompt, options=options):
                    if isinstance(message, AssistantMessage):
                        for block in message.content:
                            if isinstance(block, TextBlock):
                                result_text += block.text + "\n"
                                # Extract file paths mentioned in agent output
                                files_modified.extend(
                                    _extract_file_paths(block.text)
                                )
                                if reporter:
                                    reporter.on_agent_text(agent_name, block.text)

                            elif isinstance(block, ToolUseBlock):
                                turns += 1
                                tool_calls.append(_summarise_tool_call(block.name, block.input))
                                # Track file writes/edits directly from structured tool input —
                                # more reliable than text extraction or snapshot diff.
                                if block.name in ("Write", "Edit") and "file_path" in block.input:
                                    files_modified.append(str(block.input["file_path"]))
                                if reporter:
                                    reporter.on_agent_tool_use(
                                        agent_name, block.name, block.input
                                    )

                            elif isinstance(block, ToolResultBlock):
                                if reporter:
                                    content_str = (
                                        block.content
                                        if isinstance(block.content, str)
                                        else str(block.content)[:500]
                                    ) or ""
                                    reporter.on_agent_tool_result(
                                        agent_name,
                                        "",
                                        content_str,
                                        bool(block.is_error),
                                    )

                            elif isinstance(block, ThinkingBlock):
                                if reporter:
                                    reporter.on_agent_thinking(
                                        agent_name, block.thinking[:200]
                                    )

                    if isinstance(message, ResultMessage):
                        cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0
                        turns = getattr(message, "num_turns", turns) or turns

                logger.info("Agent %s completed. Cost: $%.4f", agent_name, cost_usd)
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    result_text=result_text.strip(),
                    files_modified=list(set(files_modified)),
                    cost_usd=cost_usd,
                    turns=turns,
                    tool_calls=tool_calls,
                )

            except Exception as e:
                logger.error("Agent %s failed: %s", agent_name, e)
                # Preserve whatever the agent output before the exception so the
                # artifact contains actionable context rather than just "exit code 1".
                failure_suffix = f"\n[FAILED: {e}]"
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    result_text=(result_text.strip() + failure_suffix) if result_text.strip() else str(e),
                    files_modified=list(set(files_modified)),
                    turns=turns,
                    tool_calls=tool_calls,
                )
            finally:
                if claudecode_val is not None:
                    os.environ["CLAUDECODE"] = claudecode_val


def _summarise_tool_call(tool_name: str, tool_input: dict) -> str:
    """Return a short human-readable string for a tool call, e.g. 'Read(src/po/foo.ts)'."""
    for key in ("file_path", "path", "filename", "pattern"):
        if key in tool_input:
            val = str(tool_input[key])
            return f"{tool_name}({val[:80]})"
    if "command" in tool_input:
        return f"{tool_name}({str(tool_input['command'])[:80]})"
    if "query" in tool_input:
        return f"{tool_name}({str(tool_input['query'])[:80]})"
    return tool_name


def _extract_file_paths(text: str) -> list[str]:
    """Heuristically extract file paths from agent output text."""
    import re

    # Match paths that look like project files (.ts, .js, .tsx, .jsx)
    pattern = re.compile(
        r"(?:wrote|created|modified|updated|edited|patched)\s+[`'\"]?"
        r"([\w/\\.-]+\.(?:ts|js|tsx|jsx))"
        r"[`'\"]?",
        re.IGNORECASE,
    )
    return [m.group(1) for m in pattern.finditer(text)]
