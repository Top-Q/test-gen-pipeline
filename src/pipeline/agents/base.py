"""Base agent runner wrapping the Claude Agent SDK."""

from __future__ import annotations

import logging
import platform
import tempfile
from contextlib import contextmanager
from dataclasses import dataclass, field
from pathlib import Path
from typing import Generator

from claude_agent_sdk import ClaudeAgentOptions, query
from claude_agent_sdk.types import AssistantMessage, ResultMessage, TextBlock

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


class AgentRunner:
    """Wrapper around claude_agent_sdk.query() for pipeline agents."""

    def __init__(self, cwd: str | Path):
        self.cwd = str(cwd)

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
        files_modified: list[str] = []

        with _system_prompt_option(system_prompt) as sp_option:
            options = ClaudeAgentOptions(
                system_prompt=sp_option,
                cwd=self.cwd,
                allowed_tools=tools,
                permission_mode=permission_mode,
                max_turns=max_turns,
                model=model,
            )

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

                    if isinstance(message, ResultMessage):
                        cost_usd = getattr(message, "total_cost_usd", 0.0) or 0.0

                logger.info("Agent %s completed. Cost: $%.4f", agent_name, cost_usd)
                return AgentResult(
                    agent_name=agent_name,
                    success=True,
                    result_text=result_text.strip(),
                    files_modified=list(set(files_modified)),
                    cost_usd=cost_usd,
                )

            except Exception as e:
                logger.error("Agent %s failed: %s", agent_name, e)
                return AgentResult(
                    agent_name=agent_name,
                    success=False,
                    result_text=str(e),
                )


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
