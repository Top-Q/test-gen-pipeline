"""Profile loader — reads YAML config, validates, merges knowledge files."""

from pathlib import Path

import yaml

from .schemas.profile_schema import ProfileConfig

PROFILES_DIR = Path(__file__).parent.parent.parent / "profiles"


def load_profile(profile_name: str, profiles_dir: Path | None = None) -> ProfileConfig:
    """Load and validate a profile by name.

    Reads profiles/<name>/profile.yaml, validates via ProfileConfig,
    and merges knowledge files from _base and profile-specific dirs.
    """
    base_dir = profiles_dir or PROFILES_DIR
    profile_dir = base_dir / profile_name
    profile_yaml = profile_dir / "profile.yaml"

    if not profile_yaml.exists():
        raise FileNotFoundError(f"Profile not found: {profile_yaml}")

    with open(profile_yaml, encoding="utf-8") as f:
        raw = yaml.safe_load(f)

    config = ProfileConfig(**raw)

    # Validate barrel export exists if specified
    if config.barrel_export:
        barrel_path = config.resolve_barrel_export()
        if barrel_path and not barrel_path.exists():
            raise FileNotFoundError(
                f"Barrel export file not found: {barrel_path}"
            )

    # Validate fixture path exists
    fixture_full = config.resolve_path(config.fixture_path)
    if not fixture_full.exists():
        raise FileNotFoundError(f"Fixture file not found: {fixture_full}")

    # Merge knowledge files: base + profile-specific (profile overrides base)
    config.knowledge_files = _merge_knowledge(base_dir, profile_name, config.knowledge_files)

    return config


def _merge_knowledge(
    base_dir: Path,
    profile_name: str,
    declared_files: dict[str, str],
) -> dict[str, str]:
    """Merge _base/knowledge/ files with profile-specific knowledge/ files.

    Profile-specific files override base files with the same stem name.
    Returns a dict of role_name → absolute file path.
    """
    merged: dict[str, str] = {}

    # Load base knowledge files
    base_knowledge = base_dir / "_base" / "knowledge"
    if base_knowledge.is_dir():
        for f in base_knowledge.iterdir():
            if f.is_file() and f.suffix == ".md":
                merged[f.stem] = str(f.resolve())

    # Load profile-specific knowledge files (override base)
    profile_knowledge = base_dir / profile_name / "knowledge"
    if profile_knowledge.is_dir():
        for f in profile_knowledge.iterdir():
            if f.is_file() and f.suffix == ".md":
                merged[f.stem] = str(f.resolve())

    # Add explicitly declared files (highest priority)
    profile_dir = base_dir / profile_name
    for role_name, rel_path in declared_files.items():
        full_path = profile_dir / rel_path
        if full_path.exists():
            merged[role_name] = str(full_path.resolve())

    return merged


def load_knowledge_content(knowledge_files: dict[str, str]) -> dict[str, str]:
    """Read all knowledge files and return role_name → content mapping."""
    content: dict[str, str] = {}
    for role_name, file_path in knowledge_files.items():
        path = Path(file_path)
        if path.exists():
            content[role_name] = path.read_text(encoding="utf-8")
    return content
