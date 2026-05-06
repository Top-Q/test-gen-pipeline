"""Deterministic validator — lint, typecheck, and structural regex checks."""

import asyncio
import fnmatch
import glob
import re
from pathlib import Path

from .schemas.profile_schema import ProfileConfig, StructuralCheck
from .schemas.run_state import ValidationResult


async def run_all_checks(
    profile: ProfileConfig,
    files: list[str],
) -> list[ValidationResult]:
    """Run all configured validation checks on the given files.

    Lint runs on *files* only.  TypeCheck runs project-wide.
    Structural checks run on *files* when provided; otherwise they fall back
    to globbing the entire project.  This prevents pre-existing files in other
    modules from causing false failures when validating newly generated code.
    """
    results: list[ValidationResult] = []

    if files:
        lint_result = await run_lint(profile, files)
        results.append(lint_result)

    typecheck_result = await run_typecheck(profile)
    results.append(typecheck_result)

    for check in profile.validation.structural_checks:
        result = run_structural_check(profile, check, generated_files=files)
        results.append(result)

    return results


async def run_lint(
    profile: ProfileConfig,
    files: list[str],
) -> ValidationResult:
    """Run the configured lint command on specified files."""
    files_str = " ".join(f'"{f}"' for f in files)
    command = profile.validation.lint_command.replace("{files}", files_str)

    return await _run_command("lint", command, profile.project_root, files)


async def run_typecheck(profile: ProfileConfig) -> ValidationResult:
    """Run the configured typecheck command."""
    command = profile.validation.typecheck_command

    return await _run_command("typecheck", command, profile.project_root)


def run_structural_check(
    profile: ProfileConfig,
    check: StructuralCheck,
    generated_files: list[str] | None = None,
) -> ValidationResult:
    """Run a single regex-based structural check against matching files.

    When *generated_files* is provided the check is scoped to those files
    (still filtered by the check's file_glob pattern).  This avoids false
    positives from pre-existing files in unrelated modules.
    """
    base = profile.project_root
    if generated_files is not None:
        # Scope to the provided files, but still honour the file_glob filter.
        # Normalise separators so fnmatch works on Windows paths.
        # An empty list means "no generated files" — pass vacuously (no violations).
        matched_files = [
            f for f in generated_files
            if fnmatch.fnmatch(f.replace("\\", "/"), check.file_glob.replace("\\", "/"))
        ]
    else:
        matched_files = glob.glob(check.file_glob, root_dir=str(base), recursive=True)
    pattern = re.compile(check.pattern)
    violations: list[str] = []

    for rel_path in matched_files:
        full_path = base / rel_path
        if not full_path.is_file():
            continue
        content = full_path.read_text(encoding="utf-8", errors="replace")

        has_match = bool(pattern.search(content))
        if check.must_match and not has_match:
            violations.append(f"{rel_path}: {check.error_message}")
        elif not check.must_match and has_match:
            violations.append(f"{rel_path}: {check.error_message}")

    passed = len(violations) == 0
    output = "\n".join(violations) if violations else "OK"

    return ValidationResult(
        check_name=check.name,
        passed=passed,
        output=output,
        files_checked=matched_files,
    )


async def _run_command(
    check_name: str,
    command: str,
    cwd: Path,
    files: list[str] | None = None,
) -> ValidationResult:
    """Execute a shell command and return a ValidationResult."""
    try:
        proc = await asyncio.create_subprocess_shell(
            command,
            cwd=str(cwd),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=120)
        output = (stdout or b"").decode("utf-8", errors="replace")
        err_output = (stderr or b"").decode("utf-8", errors="replace")
        combined = output + ("\n" + err_output if err_output else "")

        return ValidationResult(
            check_name=check_name,
            passed=proc.returncode == 0,
            output=combined.strip(),
            files_checked=files or [],
        )
    except asyncio.TimeoutError:
        return ValidationResult(
            check_name=check_name,
            passed=False,
            output=f"Command timed out after 120s: {command}",
            files_checked=files or [],
        )
    except Exception as e:
        return ValidationResult(
            check_name=check_name,
            passed=False,
            output=f"Command failed: {e}",
            files_checked=files or [],
        )
