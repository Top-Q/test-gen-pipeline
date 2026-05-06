"""Shared test fixtures and configuration."""

from pathlib import Path

import pytest

FIXTURES_DIR = Path(__file__).parent / "fixtures"
PROFILES_DIR = Path(__file__).parent.parent / "profiles"


@pytest.fixture
def fixtures_dir() -> Path:
    return FIXTURES_DIR


@pytest.fixture
def profiles_dir() -> Path:
    return PROFILES_DIR


@pytest.fixture
def sample_test_plan_path(fixtures_dir: Path) -> Path:
    return fixtures_dir / "sample_test_plan.md"
