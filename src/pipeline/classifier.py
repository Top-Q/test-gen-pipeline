"""Failure classifier — pure Python regex pattern matching on Playwright output."""

import re
from dataclasses import dataclass
from enum import StrEnum


class FailureCategory(StrEnum):
    """Categories of Playwright test failures."""

    TIMEOUT = "timeout"
    LOCATOR_NOT_FOUND = "locator_not_found"
    ASSERTION_MISMATCH = "assertion_mismatch"
    MISSING_METHOD = "missing_method"
    IMPORT_ERROR = "import_error"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


# Pattern → category mapping, checked in order
_PATTERNS: list[tuple[re.Pattern[str], FailureCategory]] = [
    (re.compile(r"waiting for locator|Timeout \d+ms exceeded|timeout", re.IGNORECASE), FailureCategory.TIMEOUT),
    (re.compile(r"strict mode violation|resolved to \d+ elements", re.IGNORECASE), FailureCategory.LOCATOR_NOT_FOUND),
    (re.compile(r"expect\(received\)|toBe|toContain|toHaveText|toBeVisible|AssertionError", re.IGNORECASE), FailureCategory.ASSERTION_MISMATCH),
    (re.compile(r"is not a function|has no property|TypeError:.*undefined", re.IGNORECASE), FailureCategory.MISSING_METHOD),
    (re.compile(r"Cannot find module|no exported member|Module not found|TS2305|TS2307", re.IGNORECASE), FailureCategory.IMPORT_ERROR),
    (re.compile(r"ECONNREFUSED|net::ERR|ENOTFOUND|ETIMEDOUT", re.IGNORECASE), FailureCategory.INFRASTRUCTURE),
]

# Category → routing destination
_ROUTING: dict[FailureCategory, str] = {
    FailureCategory.TIMEOUT: "healer",
    FailureCategory.LOCATOR_NOT_FOUND: "healer",
    FailureCategory.ASSERTION_MISMATCH: "healer",
    FailureCategory.MISSING_METHOD: "healer",
    FailureCategory.IMPORT_ERROR: "healer",
    FailureCategory.INFRASTRUCTURE: "abort",
    FailureCategory.UNKNOWN: "abort",
}


@dataclass
class ClassifiedFailure:
    """Result of classifying a test failure."""

    category: FailureCategory
    message: str
    file_paths: list[str]
    route_to: str  # "healer", "pom_builder", or "abort"


def classify_failure(error_output: str) -> ClassifiedFailure:
    """Classify a Playwright test failure based on error output patterns."""
    category = FailureCategory.UNKNOWN
    message = _extract_error_message(error_output)

    for pattern, cat in _PATTERNS:
        if pattern.search(error_output):
            category = cat
            break

    file_paths = _extract_file_paths(error_output)
    route_to = _ROUTING[category]

    return ClassifiedFailure(
        category=category,
        message=message,
        file_paths=file_paths,
        route_to=route_to,
    )


def _extract_error_message(output: str) -> str:
    """Extract the primary error message from Playwright output."""
    lines = output.strip().split("\n")
    # Look for lines starting with Error:, expect(, or containing assertion text
    for line in lines:
        stripped = line.strip()
        if stripped.startswith(("Error:", "expect(", "TypeError:", "ReferenceError:")):
            return stripped
        if "error" in stripped.lower() and len(stripped) < 200:
            return stripped

    # Fallback: first non-empty line, truncated
    for line in lines:
        if line.strip():
            return line.strip()[:200]
    return "Unknown error"


def _extract_file_paths(output: str) -> list[str]:
    """Extract file paths from stack traces in error output."""
    # Match paths like /path/to/file.ts:123:45 or at Object.<anonymous> (file.ts:10:5)
    path_pattern = re.compile(
        r"(?:at\s+.*?\(|at\s+)?"  # optional "at" prefix
        r"((?:[A-Za-z]:[\\/]|/)"  # drive letter or /
        r"[^\s:()]+\.(?:ts|js|tsx|jsx))"  # file path with extension
        r":(\d+)"  # line number
    )
    paths: list[str] = []
    seen: set[str] = set()

    for match in path_pattern.finditer(output):
        path = match.group(1)
        if path not in seen:
            seen.add(path)
            paths.append(path)

    return paths
