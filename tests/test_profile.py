"""Tests for the profile loader."""

from pathlib import Path

import pytest

from pipeline.profile import load_profile


def test_load_openproject_profile(profiles_dir: Path):
    """Load the openproject profile successfully."""
    profile = load_profile("openproject", profiles_dir)

    assert profile.name == "openproject"
    assert profile.stack == "rails"
    assert profile.barrel_export == "internals.ts"
    assert profile.base_url == "http://localhost:8090"


def test_profile_knowledge_files_merged(profiles_dir: Path):
    """Knowledge files from base and profile are merged."""
    profile = load_profile("openproject", profiles_dir)

    # Should have both base and profile-specific knowledge
    assert "failure-patterns" in profile.knowledge_files  # from _base
    assert "page-objects" in profile.knowledge_files  # from openproject
    assert "dom-quirks" in profile.knowledge_files  # from openproject


def test_profile_validation_config(profiles_dir: Path):
    """Validation config is parsed correctly."""
    profile = load_profile("openproject", profiles_dir)

    assert "eslint" in profile.validation.lint_command
    assert "tsc" in profile.validation.typecheck_command
    assert len(profile.validation.structural_checks) == 3


def test_profile_structural_checks(profiles_dir: Path):
    """Structural checks are properly configured."""
    profile = load_profile("openproject", profiles_dir)
    checks = profile.validation.structural_checks

    check_names = [c.name for c in checks]
    assert "no-expect-in-po" in check_names
    assert "locators-have-describe" in check_names
    assert "waitforload-exists" in check_names

    # no-expect-in-po should be must_match=False
    no_expect = next(c for c in checks if c.name == "no-expect-in-po")
    assert no_expect.must_match is False


def test_nonexistent_profile_raises(profiles_dir: Path):
    """Loading a non-existent profile raises FileNotFoundError."""
    with pytest.raises(FileNotFoundError):
        load_profile("nonexistent", profiles_dir)


def test_resolve_path(profiles_dir: Path):
    """resolve_path returns absolute path relative to project_root."""
    profile = load_profile("openproject", profiles_dir)
    resolved = profile.resolve_path("src/po/openproject")
    assert resolved.is_absolute()
    assert str(resolved).endswith("src/po/openproject") or str(resolved).endswith("src\\po\\openproject")
