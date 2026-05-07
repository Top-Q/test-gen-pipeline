# Test Generation Pipeline

Agentic Playwright test generation pipeline using Claude Agent SDK. Takes a **test plan** (YAML+Gherkin markdown) and a **profile** (project config + knowledge), then orchestrates AI agents to generate Page Objects, write tests, execute them, and heal failures.

## Project Layout

```
test-gen-pipeline/
├── src/pipeline/                    # Python package (pip install -e .)
│   ├── cli.py                       # Click CLI — entry point: pipeline.cli:main
│   ├── orchestrator.py              # State machine (Orchestrator class)
│   ├── profile.py                   # YAML loader + knowledge file merging
│   ├── prompt_builder.py            # Jinja2 template renderer (PromptBuilder)
│   ├── test_plan_parser.py          # YAML+Gherkin markdown parser
│   ├── pom_contract_extractor.py    # Regex-based TS class signature extraction
│   ├── validator.py                 # Lint, typecheck, structural regex checks
│   ├── classifier.py                # Failure categorization + routing
│   ├── state.py                     # JSON state persistence (StateManager)
│   ├── agents/
│   │   ├── base.py                  # AgentRunner — wraps claude_agent_sdk.query()
│   │   ├── pom_builder.py           # POM Builder agent
│   │   ├── test_writer.py           # Test Writer agent
│   │   └── healer.py               # Healer agent
│   └── schemas/
│       ├── profile_schema.py        # ProfileConfig, AuthConfig, ValidationConfig, StructuralCheck
│       ├── run_state.py             # RunState, PipelineState, AgentInvocation, TestResult, FailureRecord, ValidationResult
│       ├── test_plan.py             # TestPlan, TestScenario
│       └── pom_contract.py          # PomContract, PomMethod
├── prompt-templates/                # Jinja2 agent system prompts
│   ├── pom_builder.md.j2
│   ├── test_writer.md.j2
│   └── healer.md.j2
├── profiles/
│   ├── _base/knowledge/             # Shared knowledge (inherited by all profiles)
│   │   ├── browser-tools.md         # playwright-cli usage for live DOM inspection
│   │   ├── failure-patterns.md      # Common Playwright failure patterns
│   │   └── test-structure.md        # Test file conventions
│   └── openproject/                 # OpenProject profile
│       ├── profile.yaml             # Profile configuration
│       └── knowledge/               # Profile-specific knowledge (overrides _base by stem)
│           ├── architecture.md      # Project architecture rules
│           ├── page-objects.md      # PO class templates & patterns
│           ├── components.md        # Component class templates
│           ├── locator-patterns.md  # Locator selector strategies
│           ├── module-scaffold.md   # New module creation checklist
│           ├── dom-quirks.md        # Runtime DOM behavior specifics
│           ├── source-code-map.md   # Where to find source files & element IDs
│           └── test-structure.md    # Test writing conventions (overrides _base)
├── artifacts/                       # Run output — one directory per execution
│   └── <YYYYMMdd-HHMMSS-shortid>/
│       └── run_state.json
├── tests/fixtures/                  # Sample test plans for development
│   └── sample_test_plan.md
└── pyproject.toml                   # Python package config & CLI entry point
```

## CLI

Entry point: `pipeline = pipeline.cli:main` (installed via `pip install -e .`).

```bash
# Full pipeline
pipeline [-v] run --profile <name> --plan <path> [--ci] [--resume <run-id>]
    [--profiles-dir <dir>] [--artifacts-dir <dir>]

# Individual steps
pipeline [-v] build-pom --profile <name> --plan <path> [--ci]
pipeline [-v] write-test --profile <name> --plan <path> [--ci]
pipeline [-v] validate --profile <name> --files "<glob-or-paths>"
pipeline [-v] heal --profile <name> --run-id <id> [--ci]
```

- `-v` enables DEBUG logging (to stderr)
- `--ci` sets `permission_mode="bypassPermissions"` (no interactive prompts)
- JSON result goes to stdout; logs go to stderr
- Exit code: 0 = success, 1 = failure

## State Machine

The `Orchestrator` drives through these states (defined in `PipelineState` StrEnum):

```
ANALYZE_PLAN → CHECK_POM → [BUILD_POM → VALIDATE_POM →] WRITE_TEST → VALIDATE_TEST → RUN_TEST → DONE
                                                                                         │
                                                                               (if tests fail)
                                                                                         ↓
                                                                              CLASSIFY_FAILURE
                                                                               ↙            ↘
                                                                           HEAL          FAILED
                                                                            ↓
                                                                        RUN_TEST (loop)
```

### State transitions

| State | What happens | Next state |
|-------|-------------|------------|
| `analyze_plan` | Validates the test plan has scenarios | `check_pom` (or `failed` if empty) |
| `check_pom` | Checks if PO directories exist for all `component` values in the plan | `build_pom` if missing, `write_test` if all exist. Creates git branch. |
| `build_pom` | Invokes POM Builder agent. Extracts existing PO contracts and test plan summary. | `validate_pom` on success, `failed` if max attempts reached. If agent fails but PO files were created, retries. |
| `validate_pom` | Runs lint, typecheck, structural checks on generated PO files | `write_test` on pass, `failed` on fail (no retry — agent should self-correct) |
| `write_test` | Invokes Test Writer agent. Passes POM contracts JSON + full test plan text. Detects new spec files via filesystem diff. | `validate_test` on success |
| `validate_test` | Runs lint, typecheck, structural checks on generated test files | `run_test` on pass, retries `write_test` if attempts remain |
| `run_test` | Runs `npx playwright test <files> --reporter=json` (300s timeout). Parses JSON report for error messages. | `done` if all pass, `classify_failure` if any fail |
| `classify_failure` | Regex-classifies errors, checks for repeated identical failures | `heal`, `build_pom`, or `failed` depending on category |
| `heal` | Invokes Healer agent with error output, category, and relevant files. Then validates patched files. | `run_test` on success |
| `done` | Terminal — all tests passed | — |
| `failed` | Terminal — unrecoverable error or max attempts | — |

### Guardrails

| Limit | Value |
|-------|-------|
| Max total agent invocations | 8 |
| Max POM Builder attempts | 3 |
| Max Test Writer attempts | 3 |
| Max Healer attempts | 2 |

### Git branch

On first `check_pom`, creates branch `pipeline/<run-id>` in the target project.

## Agents

All agents use `claude_agent_sdk.query()` via the `AgentRunner` wrapper in `agents/base.py`. On Windows, system prompts exceeding 8000 chars are written to temp files to avoid `WinError 206`.

| Agent | Module | Model | Max Turns | Tools | Responsibility |
|-------|--------|-------|-----------|-------|----------------|
| POM Builder | `agents/pom_builder.py` | `claude-sonnet-4-20250514` | 30 | Read, Write, Edit, Glob, Grep, Bash | Generate Page Object and Component `.ts` files |
| Test Writer | `agents/test_writer.py` | `claude-sonnet-4-20250514` | 20 | Read, Write, Edit, Glob, Grep, Bash | Generate `.spec.ts` test files |
| Healer | `agents/healer.py` | `claude-sonnet-4-20250514` | 8 | Read, Edit, Bash, Glob, Grep | Apply minimal patches to fix test failures (no Write — edits only) |

### Agent invocation flow

1. `PromptBuilder.render()` loads Jinja2 template + profile knowledge → system prompt
2. Agent-specific class builds user prompt (fixed instruction string)
3. `AgentRunner.invoke()` calls `claude_agent_sdk.query()` with model, tools, max_turns
4. Streams `AssistantMessage` blocks, extracts file paths from text via regex
5. Returns `AgentResult(success, result_text, files_modified, cost_usd)`

### Agent result: `AgentResult`

```python
@dataclass
class AgentResult:
    agent_name: str
    success: bool
    result_text: str
    files_modified: list[str] = []
    cost_usd: float = 0.0
```

## Prompt Templates (Jinja2)

Located in `prompt-templates/`. Each template receives `profile` (ProfileConfig), `knowledge` (dict[str, str]), and agent-specific context.

### `pom_builder.md.j2`

Receives: `test_plan_summary`, `existing_po_summary`

Injects knowledge: `source-code-map`, `browser-tools`, `architecture`, `page-objects`, `components`, `locator-patterns`, `module-scaffold`, `dom-quirks`

Key rules in the template: read source code before writing locators, use playwright-cli to take snapshots, prefer element IDs when available, all POs extend BasePage, all components extend BaseComponent.

### `test_writer.md.j2`

Receives: `test_plan_text`, `pom_contracts_json`

Injects knowledge: `test-structure`, `fixtures`

Key rules: use only methods from POM contracts JSON, import from barrel export, use fixtures not beforeEach, create files in `<test_dir>/<component-name>/`.

### `healer.md.j2`

Receives: `error_output`, `failure_category`, `relevant_files`

Injects knowledge: `source-code-map`, `dom-quirks`, `browser-tools`, `locator-patterns`

Key rules: minimal patch only, no refactoring, no new files, edit existing only, use playwright-cli for locator investigation.

## Profiles

### Schema (`ProfileConfig`)

```yaml
name: string                    # Profile identifier
stack: string                   # rails/angular/react/vue/nextjs
project_root: Path              # Absolute path to target Playwright project (must exist)
po_base_dir: string             # Relative to project_root (e.g. "src/po/openproject")
test_dir: string                # Relative to project_root (e.g. "tests/ui")
barrel_export: string | null    # Relative to project_root (e.g. "internals.ts"), optional
fixture_path: string            # Relative to project_root (e.g. "tests/ui/fixtures.ts")
base_url: string                # App URL (e.g. "http://localhost:8090")
auth:
  strategy: string              # "session_cookie", "api_key", "basic"
  username: string
  password: string
  api_key: string
validation:
  lint_command: string           # Template with {files} placeholder
  typecheck_command: string      # Runs project-wide (no {files})
  structural_checks: list        # Regex-based checks (see below)
knowledge_files: dict            # Optional explicit role→path overrides
```

### Structural checks

Each check has: `name`, `pattern` (regex), `file_glob`, `must_match` (bool), `error_message`.
- `must_match: true` — pattern must exist in every matched file
- `must_match: false` — pattern must NOT exist in any matched file

### Profile loading (`profile.py`)

1. Reads `profiles/<name>/profile.yaml` → validates with `ProfileConfig`
2. Validates `barrel_export` and `fixture_path` exist on disk
3. Merges knowledge: `_base/knowledge/*.md` + `<name>/knowledge/*.md` (profile overrides base by stem name)
4. Explicitly declared `knowledge_files` in YAML take highest priority
5. Returns `ProfileConfig` with `knowledge_files` as `dict[str, str]` (role → absolute path)

### Current profile: OpenProject

```yaml
name: openproject
stack: rails
project_root: "C:\\Users\\itaiag\\git\\node\\playwright-typescript"
po_base_dir: src/po/openproject
test_dir: tests/ui
barrel_export: internals.ts
fixture_path: tests/ui/fixtures.ts
base_url: "http://localhost:8090"
auth:
  strategy: session_cookie
  username: admin
  password: admin
```

## Knowledge Files

Markdown files injected into agent system prompts. Loaded by `profile.py`, read by `prompt_builder.py` via `load_knowledge_content()`.

### Merging rules

1. All `.md` files in `profiles/_base/knowledge/` are loaded (stem name = role)
2. All `.md` files in `profiles/<name>/knowledge/` are loaded (override base by stem)
3. Explicit entries in `knowledge_files:` YAML take highest priority

### Knowledge roles and which agents use them

| Role (stem) | Used by | Purpose |
|-------------|---------|---------|
| `architecture` | POM Builder | Project architecture rules & patterns |
| `page-objects` | POM Builder | PO class templates |
| `components` | POM Builder | Component class templates |
| `locator-patterns` | POM Builder, Healer | Locator selector strategies |
| `module-scaffold` | POM Builder | New module creation checklist |
| `dom-quirks` | POM Builder, Healer | Runtime DOM behavior specifics |
| `source-code-map` | POM Builder, Healer | Where to find source files & element IDs |
| `browser-tools` | POM Builder, Healer | playwright-cli commands for live DOM inspection |
| `test-structure` | Test Writer | Test file patterns & fixture usage |
| `fixtures` | Test Writer | Fixture patterns (if defined) |
| `failure-patterns` | (available to all) | Common Playwright failure patterns |

## Test Plan Format

Multi-document markdown with YAML frontmatter + Gherkin body, separated by `---`.

```markdown
---
id: TEST-001
suite: MySuite
feature: Feature Name
component: module_name        # Maps to src/po/openproject/<component>/ directory
priority: P1                  # P1, P2, P3
tags: [ui, regression]
variables:
  itemName: "test-item-<uuid4>"    # <uuid4> gets unique value at runtime
setup:
  - create_item: { name: "{{ itemName }}" }  # API preconditions
---

Background:
  Given the user is authenticated as "default"
  And the user is on the Feature page

Scenario: Create a new item
  When the user creates a new item with name "<itemName>"
  Then the item appears in the list with name "<itemName>"
```

### Parsed schema (`TestPlan`, `TestScenario`)

```python
class TestScenario:
    id: str                    # "TEST-001"
    suite: str                 # "MySuite"
    feature: str               # "Feature Name"
    component: str             # "module_name"
    priority: str              # "P1"
    tags: list[str]            # ["ui", "regression"]
    variables: dict[str, str]  # {"itemName": "test-item-<uuid4>"}
    setup: list[dict]          # [{"create_item": {"name": "{{ itemName }}"}}]
    background: str            # Raw Background section text
    scenario_name: str         # "Create a new item"
    steps: list[str]           # ["When the user creates...", "Then the item..."]

class TestPlan:
    source_file: str
    scenarios: list[TestScenario]
    components -> set[str]     # Unique component names
    suites -> set[str]         # Unique suite names
```

## POM Contract Extraction

`pom_contract_extractor.py` uses regex to extract lightweight TypeScript class signatures from existing PO/component files. This is fed to agents so they know what already exists.

### What it extracts

- **Class name and extends**: `export class FooPage extends BasePage<FooPage>`
- **Async methods**: name, parameter signature, return type, JSDoc
- **Getter methods**: methods returning `Locator` (getter-style)

### Schema (`PomContract`, `PomMethod`)

```python
class PomMethod:
    name: str           # "clickSave"
    signature: str      # "(email: string, role: string)"
    returns: str        # "Promise<void>", "Locator"
    description: str    # From JSDoc
    is_getter: bool     # True for locator getters

class PomContract:
    class_name: str     # "MembersPage"
    file_path: str      # Relative to project root
    extends: str        # "BasePage<MembersPage>"
    methods: list[PomMethod]
    getter_locators -> list[PomMethod]  # Filtered: is_getter=True
    action_methods -> list[PomMethod]   # Filtered: is_getter=False
```

`contracts_to_json()` serializes contracts list to JSON for embedding in agent prompts.

## Failure Classification

`classifier.py` uses regex patterns to categorize Playwright error output and decide routing.

### Categories and routing

| Category | Pattern matches | Routed to |
|----------|----------------|-----------|
| `timeout` | "waiting for locator", "Timeout Nms exceeded" | `healer` |
| `locator_not_found` | "strict mode violation", "resolved to N elements" | `healer` |
| `assertion_mismatch` | "expect(received)", "toBe", "toContain", etc. | `healer` |
| `missing_method` | "is not a function", "has no property", "TypeError" | `pom_builder` |
| `import_error` | "Cannot find module", "no exported member", TS errors | `pom_builder` |
| `infrastructure` | "ECONNREFUSED", "net::ERR", "ENOTFOUND" | `abort` |
| `unknown` | No pattern matched | `abort` |

The classifier also extracts file paths from stack traces and the primary error message line.

Repeated identical failures (same category + message) are detected and cause immediate abort.

## Validation

`validator.py` runs three types of checks:

1. **Lint** — runs `lint_command` on specified files only (`{files}` placeholder replaced)
2. **TypeCheck** — runs `typecheck_command` project-wide (no file scoping)
3. **Structural checks** — regex pattern matching on generated files, scoped by `file_glob`

All checks return `ValidationResult(check_name, passed, output, files_checked)`.

When `generated_files` is provided to structural checks, the check is scoped to those files only (avoids false positives from pre-existing files in other modules).

## Run State Persistence

`state.py` manages JSON-based state with crash recovery.

### Run ID format

`YYYYMMdd-HHMMSS-<8-char-uuid>` (e.g. `20260507-112651-022132dc`)

### State file location

`artifacts/<run-id>/run_state.json`

### RunState schema

```python
class RunState:
    run_id: str
    profile_name: str
    test_plan_path: str
    state: PipelineState           # Current state in the machine
    git_branch: str                # Created by orchestrator
    generated_po_files: list[str]  # Relative paths
    generated_test_files: list[str]
    agent_invocations: list[AgentInvocation]
    validation_results: list[ValidationResult]
    test_results: list[TestResult]
    failure_history: list[FailureRecord]
    pom_builder_attempts: int
    test_writer_attempts: int
    healer_attempts: int
    created_at: str                # ISO 8601
    updated_at: str
    total_agent_invocations -> int # len(agent_invocations)
```

### Sub-schemas

```python
class AgentInvocation:
    agent_name: str        # "pom_builder", "test_writer", "healer"
    state: str             # Pipeline state when invoked
    timestamp: str         # ISO 8601
    success: bool
    files_modified: list[str]
    error: str

class TestResult:
    passed: bool
    total: int
    failed_count: int
    error_output: str      # Human-readable error text (up to 10 unique messages)
    json_report: dict|None # Full Playwright JSON reporter output

class FailureRecord:
    category: str          # FailureCategory value
    message: str           # Primary error message
    file_paths: list[str]  # From stack traces
    routed_to: str         # "healer", "pom_builder", "abort"

class ValidationResult:
    check_name: str        # "lint", "typecheck", or structural check name
    passed: bool
    output: str
    files_checked: list[str]
```

## Dependencies

From `pyproject.toml`:
- `claude-agent-sdk>=0.1.0`
- `pydantic>=2.0`
- `pyyaml>=6.0`
- `jinja2>=3.1`
- `click>=8.1`

Peer dependency: `@playwright/cli` (npm, for live DOM inspection by agents)
