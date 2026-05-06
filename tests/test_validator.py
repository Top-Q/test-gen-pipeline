"""Tests for the deterministic validator (structural checks only)."""

import tempfile
from pathlib import Path

from pipeline.schemas.profile_schema import ProfileConfig, StructuralCheck, ValidationConfig
from pipeline.validator import run_structural_check


def _make_profile(tmp_path: Path, checks: list[StructuralCheck]) -> ProfileConfig:
    """Create a minimal profile for testing structural checks."""
    return ProfileConfig(
        name="test",
        stack="rails",
        project_root=tmp_path,
        po_base_dir="src/po",
        test_dir="tests",
        fixture_path="tests/fixtures.ts",
        base_url="http://localhost:8080",
        validation=ValidationConfig(structural_checks=checks),
    )


def test_structural_check_must_match_passes(tmp_path: Path):
    """Pattern must_match=True passes when pattern is found."""
    # Create a file with the required pattern
    po_dir = tmp_path / "src" / "po"
    po_dir.mkdir(parents=True)
    (po_dir / "example.ts").write_text("async waitForLoad(): Promise<ExamplePage> {")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "fixtures.ts").write_text("")

    check = StructuralCheck(
        name="waitforload-exists",
        pattern=r"async waitForLoad\(",
        file_glob="src/po/**/*.ts",
        must_match=True,
        error_message="Must implement waitForLoad",
    )

    profile = _make_profile(tmp_path, [check])
    result = run_structural_check(profile, check)
    assert result.passed


def test_structural_check_must_match_fails(tmp_path: Path):
    """Pattern must_match=True fails when pattern is NOT found."""
    po_dir = tmp_path / "src" / "po"
    po_dir.mkdir(parents=True)
    (po_dir / "example.ts").write_text("export class Example {}")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "fixtures.ts").write_text("")

    check = StructuralCheck(
        name="waitforload-exists",
        pattern=r"async waitForLoad\(",
        file_glob="src/po/**/*.ts",
        must_match=True,
        error_message="Must implement waitForLoad",
    )

    profile = _make_profile(tmp_path, [check])
    result = run_structural_check(profile, check)
    assert not result.passed
    assert "Must implement waitForLoad" in result.output


def test_structural_check_must_not_match_passes(tmp_path: Path):
    """Pattern must_match=False passes when pattern is NOT found."""
    po_dir = tmp_path / "src" / "po"
    po_dir.mkdir(parents=True)
    (po_dir / "example.ts").write_text("import { BasePage } from '../basePage';")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "fixtures.ts").write_text("")

    check = StructuralCheck(
        name="no-expect-in-po",
        pattern=r"import.*expect.*from.*@playwright/test",
        file_glob="src/po/**/*.ts",
        must_match=False,
        error_message="POs must not import expect",
    )

    profile = _make_profile(tmp_path, [check])
    result = run_structural_check(profile, check)
    assert result.passed


def test_structural_check_must_not_match_fails(tmp_path: Path):
    """Pattern must_match=False fails when pattern IS found."""
    po_dir = tmp_path / "src" / "po"
    po_dir.mkdir(parents=True)
    (po_dir / "bad.ts").write_text("import { expect } from '@playwright/test';")
    (tmp_path / "tests").mkdir()
    (tmp_path / "tests" / "fixtures.ts").write_text("")

    check = StructuralCheck(
        name="no-expect-in-po",
        pattern=r"import.*expect.*from.*@playwright/test",
        file_glob="src/po/**/*.ts",
        must_match=False,
        error_message="POs must not import expect",
    )

    profile = _make_profile(tmp_path, [check])
    result = run_structural_check(profile, check)
    assert not result.passed
    assert "POs must not import expect" in result.output
