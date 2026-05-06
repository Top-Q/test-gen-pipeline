"""Profile configuration schema for customer projects."""

from pathlib import Path

from pydantic import BaseModel, field_validator


class AuthConfig(BaseModel):
    """Authentication configuration."""

    strategy: str  # e.g. "session_cookie", "api_key", "basic"
    username: str = ""
    password: str = ""
    api_key: str = ""


class StructuralCheck(BaseModel):
    """A regex-based structural validation rule."""

    name: str
    pattern: str  # regex pattern
    file_glob: str  # glob to select files to check
    must_match: bool  # True = pattern must exist; False = pattern must NOT exist
    error_message: str


class ValidationConfig(BaseModel):
    """Validation commands and structural checks."""

    lint_command: str = "npx eslint {files}"
    typecheck_command: str = "npx tsc --noEmit"
    structural_checks: list[StructuralCheck] = []


class ProfileConfig(BaseModel):
    """Full profile configuration for a customer project."""

    name: str
    stack: str  # rails/angular/react/vue/nextjs
    project_root: Path
    po_base_dir: str  # relative to project_root
    test_dir: str  # relative to project_root
    barrel_export: str | None = None  # relative to project_root (e.g. "internals.ts")
    fixture_path: str  # relative to project_root
    base_url: str
    auth: AuthConfig = AuthConfig(strategy="session_cookie")
    validation: ValidationConfig = ValidationConfig()
    knowledge_files: dict[str, str] = {}  # role name → file path within profile dir

    @field_validator("project_root")
    @classmethod
    def project_root_must_exist(cls, v: Path) -> Path:
        if not v.exists():
            raise ValueError(f"project_root does not exist: {v}")
        return v

    def resolve_path(self, relative: str) -> Path:
        """Resolve a relative path against project_root."""
        return self.project_root / relative

    def resolve_barrel_export(self) -> Path | None:
        """Resolve barrel export file path, or None if not configured."""
        if self.barrel_export is None:
            return None
        return self.resolve_path(self.barrel_export)
