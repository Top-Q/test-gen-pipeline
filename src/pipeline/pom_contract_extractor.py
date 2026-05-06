"""POM contract extractor — regex-based TS class signature extraction."""

import re
from pathlib import Path

from .schemas.pom_contract import PomContract, PomMethod


def extract_contracts(file_paths: list[str | Path]) -> list[PomContract]:
    """Extract POM contracts from a list of TypeScript files."""
    contracts: list[PomContract] = []
    for fp in file_paths:
        path = Path(fp)
        if not path.exists() or not path.suffix == ".ts":
            continue
        content = path.read_text(encoding="utf-8", errors="replace")
        contract = _extract_from_content(content, str(fp))
        if contract:
            contracts.append(contract)
    return contracts


def extract_contracts_from_dir(
    directory: Path, project_root: Path | None = None
) -> list[PomContract]:
    """Extract POM contracts from all .ts files in a directory tree."""
    contracts: list[PomContract] = []
    for ts_file in directory.rglob("*.ts"):
        content = ts_file.read_text(encoding="utf-8", errors="replace")
        rel_path = str(ts_file.relative_to(project_root)) if project_root else str(ts_file)
        contract = _extract_from_content(content, rel_path)
        if contract:
            contracts.append(contract)
    return contracts


def _extract_from_content(content: str, file_path: str) -> PomContract | None:
    """Extract a PomContract from a single TS file's content."""
    # Match: export class FooPage extends BasePage<FooPage>
    class_match = re.search(
        r"export\s+class\s+(\w+)\s+extends\s+([\w<>]+)",
        content,
    )
    if not class_match:
        return None

    class_name = class_match.group(1)
    extends = class_match.group(2)

    methods = _extract_methods(content)

    return PomContract(
        class_name=class_name,
        file_path=file_path,
        extends=extends,
        methods=methods,
    )


def _extract_methods(content: str) -> list[PomMethod]:
    """Extract method signatures from TS class content."""
    methods: list[PomMethod] = []

    # Extract async methods: async methodName(params): Promise<ReturnType>
    async_pattern = re.compile(
        r"(?:/\*\*\s*(.*?)\s*\*/\s*)?"  # optional JSDoc
        r"(?:private\s+|protected\s+|public\s+)?"  # optional access modifier
        r"async\s+(\w+)\s*(\([^)]*\))\s*:\s*(Promise<[^{]+?>)",
        re.DOTALL,
    )
    for m in async_pattern.finditer(content):
        jsdoc = (m.group(1) or "").strip().replace("\n", " ").replace("*", "").strip()
        methods.append(PomMethod(
            name=m.group(2),
            signature=m.group(3).strip(),
            returns=m.group(4).strip(),
            description=jsdoc,
            is_getter=False,
        ))

    # Extract getter-style methods that return Locator
    # Pattern: get fooLocator(): Locator  or  getFoo(): Locator
    getter_pattern = re.compile(
        r"(?:/\*\*\s*(.*?)\s*\*/\s*)?"  # optional JSDoc
        r"(?:private\s+|protected\s+|public\s+)?"
        r"(?:get\s+)?(\w+)\s*\(\s*\)\s*(?::\s*(Locator)\b)",
        re.DOTALL,
    )
    for m in getter_pattern.finditer(content):
        name = m.group(2)
        returns = m.group(3) or "Locator"
        # Skip if already captured as async method
        if any(existing.name == name for existing in methods):
            continue
        jsdoc = (m.group(1) or "").strip().replace("\n", " ").replace("*", "").strip()
        methods.append(PomMethod(
            name=name,
            signature="()",
            returns=returns,
            description=jsdoc,
            is_getter=True,
        ))

    return methods


def contracts_to_json(contracts: list[PomContract]) -> str:
    """Serialize contracts to JSON for embedding in prompts."""
    import json

    return json.dumps(
        [c.model_dump() for c in contracts],
        indent=2,
    )
