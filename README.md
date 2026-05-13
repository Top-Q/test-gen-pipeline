# Test Generation Pipeline

An agentic Playwright test generation pipeline using the Claude Agent SDK. Automatically generates Page Objects, writes end-to-end tests, executes them, and heals failures using AI agents.

## Overview

This pipeline takes a **test plan** (YAML+Gherkin markdown) and a **profile** (project configuration + knowledge files) and orchestrates Claude agents to:

1. **Analyze** the test plan and project structure
2. **Build** Page Objects and Component classes from your application source
3. **Write** Playwright test specs based on Gherkin scenarios
4. **Validate** generated TypeScript code (lint, typecheck, structural checks)
5. **Execute** tests using Playwright
6. **Heal** test failures by analyzing errors and applying minimal fixes

## Quick Start

### Prerequisites

- Python 3.11+
- Node.js 18+ (for Playwright)
- An existing Playwright TypeScript project
- Claude API key (`ANTHROPIC_API_KEY` environment variable)

### Installation

```bash
# Clone and install
git clone <repo-url>
cd test-gen-pipeline
pip install -e .
```

### Basic Usage

```bash
# Run the full pipeline
pipeline run --profile openproject --plan tests/fixtures/sample_test_plan.md

# Or run individual steps
pipeline build-pom --profile openproject --plan tests/fixtures/sample_test_plan.md
pipeline write-test --profile openproject --plan tests/fixtures/sample_test_plan.md
pipeline validate --profile openproject --files "src/po/openproject/**/*.ts"
pipeline heal --profile openproject --run-id 20260513-120000-abcd1234
```

Enable debug logging with `-v`:

```bash
pipeline -v run --profile openproject --plan tests/fixtures/sample_test_plan.md
```

## Test Plans

Test plans are markdown files with YAML frontmatter followed by Gherkin scenarios.

### Example

```markdown
---
id: TEST-001
suite: Dashboard
feature: User Dashboard
component: dashboard
priority: P1
tags: [ui, regression]
variables:
  dashboardTitle: "My Dashboard"
setup:
  - login: { username: "admin", password: "admin" }
---

Background:
  Given the user is authenticated
  And the user is on the dashboard page

Scenario: View dashboard widgets
  When the user opens the dashboard
  Then they see the main widgets
  And the dashboard title displays "My Dashboard"

Scenario: Add a widget
  When the user clicks "Add Widget"
  And the user selects "Calendar" from the widget menu
  Then the calendar widget appears on the dashboard
```

### Test Plan Schema

- `id` - Unique test identifier
- `suite` - Test suite name
- `feature` - Feature description
- `component` - Maps to a directory in `po_base_dir`
- `priority` - P1, P2, or P3
- `tags` - Searchable test tags
- `variables` - Test data (supports `<uuid4>` for unique values)
- `setup` - API preconditions (optional)
- `Background` - Gherkin background steps
- `Scenario` - Test scenarios in Gherkin format

## Profiles

Profiles define how the pipeline should work with your project. Each profile contains:

- Project paths (root, PO directory, test directory)
- Playwright base URL and authentication
- Validation commands and structural checks
- Knowledge files (embedded in agent prompts)

### Creating a Profile

1. Create `profiles/<name>/profile.yaml`:

```yaml
name: myproject
stack: react
project_root: "/path/to/playwright-project"
po_base_dir: src/po/myproject
test_dir: tests/ui
barrel_export: internals.ts
fixture_path: tests/ui/fixtures.ts
base_url: "http://localhost:3000"

auth:
  strategy: session_cookie
  username: testuser
  password: testpass123

validation:
  lint_command: "eslint {files} --max-warnings=0"
  typecheck_command: "tsc --noEmit"
  structural_checks:
    - name: "extends BasePage"
      pattern: "extends BasePage<"
      file_glob: "src/po/**/*.ts"
      must_match: true
      error_message: "All page objects must extend BasePage<T>"
```

2. Create knowledge files in `profiles/<name>/knowledge/`:

- `architecture.md` - Project architecture and patterns
- `page-objects.md` - Page Object class templates
- `components.md` - Component class patterns
- `locator-patterns.md` - How to find elements in your app
- `source-code-map.md` - Where to find element IDs and source code
- `dom-quirks.md` - Runtime DOM behavior specifics
- `test-structure.md` - Test file conventions (overrides base)

Knowledge files are injected into agent system prompts to guide code generation.

## Project Structure

```
test-gen-pipeline/
├── src/pipeline/              # Main Python package
│   ├── cli.py                 # Click CLI entry point
│   ├── orchestrator.py        # State machine orchestrator
│   ├── profile.py             # Profile loading & merging
│   ├── prompt_builder.py      # Jinja2 prompt rendering
│   ├── test_plan_parser.py    # YAML+Gherkin parser
│   ├── pom_contract_extractor.py  # TypeScript signature extraction
│   ├── validator.py           # Lint, typecheck, structural checks
│   ├── classifier.py          # Failure categorization
│   ├── state.py               # JSON state persistence
│   ├── agents/
│   │   ├── base.py            # AgentRunner wrapper
│   │   ├── pom_builder.py     # Page Object builder agent
│   │   ├── test_writer.py     # Test writer agent
│   │   └── healer.py          # Failure healer agent
│   └── schemas/
│       ├── profile_schema.py  # Configuration schemas
│       ├── run_state.py       # Pipeline state schemas
│       ├── test_plan.py       # Test plan schemas
│       └── pom_contract.py    # POM contract schemas
├── prompt-templates/          # Jinja2 agent system prompts
│   ├── pom_builder.md.j2
│   ├── test_writer.md.j2
│   └── healer.md.j2
├── profiles/                  # Profile configurations
│   ├── _base/knowledge/       # Shared knowledge files
│   └── openproject/           # OpenProject profile example
├── artifacts/                 # Run outputs (state files)
├── tests/fixtures/            # Sample test plans
└── pyproject.toml             # Package configuration
```

## State Machine

The pipeline progresses through these states:

```
ANALYZE_PLAN → CHECK_POM → [BUILD_POM → VALIDATE_POM →] WRITE_TEST
    → VALIDATE_TEST → RUN_TEST → DONE

                                      ↓ (if tests fail)
                            CLASSIFY_FAILURE
                             ↙            ↘
                         HEAL          FAILED
                          ↓
                      RUN_TEST (retry)
```

### Key States

- **ANALYZE_PLAN** - Validates test plan format and content
- **CHECK_POM** - Checks if Page Object directories exist
- **BUILD_POM** - AI agent generates Page Objects and Components
- **VALIDATE_POM** - Lint, typecheck, structural validation
- **WRITE_TEST** - AI agent writes test specs
- **VALIDATE_TEST** - Validate generated tests
- **RUN_TEST** - Execute tests with Playwright
- **CLASSIFY_FAILURE** - Categorize errors and decide next action
- **HEAL** - AI agent applies minimal fixes to failing tests
- **DONE/FAILED** - Terminal states

## Agents

Three Claude agents drive the pipeline:

### POM Builder
- **Model**: claude-sonnet-4-20250514
- **Max turns**: 30
- **Responsibility**: Generate Page Object and Component TypeScript classes
- **Tools**: Read, Write, Edit, Glob, Grep, Bash
- **Knowledge**: Architecture, page-objects, components, locators, source-code-map, browser-tools

### Test Writer
- **Model**: claude-sonnet-4-20250514
- **Max turns**: 20
- **Responsibility**: Write Playwright test specs from Gherkin scenarios
- **Tools**: Read, Write, Edit, Glob, Grep, Bash
- **Knowledge**: Test structure, fixtures, POM contracts

### Healer
- **Model**: claude-sonnet-4-20250514
- **Max turns**: 8
- **Responsibility**: Fix failing tests with minimal patches
- **Tools**: Read, Edit, Bash, Glob, Grep
- **Knowledge**: Locators, DOM quirks, browser-tools, source-code-map

## Validation

The pipeline validates generated code at multiple stages:

### Lint
Runs your project's linter (e.g., `eslint`) on generated files only.

### TypeCheck
Runs TypeScript compiler (`tsc`) project-wide to catch type errors.

### Structural Checks
Regex-based validation to ensure generated code follows patterns:
- All Page Objects extend `BasePage<T>`
- All Components extend `BaseComponent`
- Proper import statements
- Fixture usage patterns

Define structural checks in your profile's `validation.structural_checks`.

## Failure Handling

When tests fail, the classifier categorizes errors:

| Category | Examples | Action |
|----------|----------|--------|
| `timeout` | Waiting for element timeout | Heal (adjust waits/locators) |
| `locator_not_found` | Element not found, strict mode | Heal (fix selectors) |
| `assertion_mismatch` | Assertion failed | Heal (update expectations) |
| `missing_method` | Method doesn't exist | Rebuild POM (regenerate classes) |
| `import_error` | Module/import issues | Rebuild POM |
| `infrastructure` | Network/connection errors | Abort (cannot fix) |
| `unknown` | Unrecognized error | Abort |

Repeated identical failures are detected and cause immediate abort.

## API Reference

### CLI Commands

```bash
# Full pipeline
pipeline run --profile <name> --plan <path> [--ci] [--resume <run-id>]

# Individual steps
pipeline build-pom --profile <name> --plan <path> [--ci]
pipeline write-test --profile <name> --plan <path> [--ci]
pipeline validate --profile <name> --files "<glob>"
pipeline heal --profile <name> --run-id <id> [--ci]
```

### Options

- `-v, --verbose` - Enable DEBUG logging
- `--ci` - Bypass interactive prompts (for CI/CD)
- `--profiles-dir` - Override profiles directory (default: `profiles/`)
- `--artifacts-dir` - Override artifacts directory (default: `artifacts/`)
- `--resume` - Resume a previous run by ID

### Exit Codes

- `0` - Success (all tests passed)
- `1` - Failure (validation error, max retries exceeded, or unrecoverable error)

## Configuration

### Environment Variables

- `ANTHROPIC_API_KEY` - Claude API key (required)
- `PROJECT_ROOT` - Override project root (optional)

### Profile YAML Schema

See `src/pipeline/schemas/profile_schema.py` for complete schema with validation rules.

## Troubleshooting

### Agent runs out of turns
- Check that generated code is correct and executable
- Review agent prompts and knowledge files for clarity
- Consider breaking complex test plans into smaller scenarios

### TypeScript compilation errors
- Verify PO barrel export path exists
- Ensure imports match your project structure
- Check TypeScript configuration in project

### Playwright timeout errors
- Increase waits in locator patterns knowledge
- Review DOM quirks for timing issues
- Check if application is running on configured base URL

### Tests always fail with same error
- Pipeline will detect repeated failures and abort
- Review error output and knowledge files
- May need to manually inspect application with playwright-cli

## Development

### Project Setup

```bash
# Install with dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/

# Run CLI from source
python -m pipeline.cli run --profile openproject --plan tests/fixtures/sample_test_plan.md
```

### Adding a New Profile

1. Create `profiles/myprofile/profile.yaml`
2. Add knowledge files in `profiles/myprofile/knowledge/`
3. Test with: `pipeline run --profile myprofile --plan <test-plan>`

### Modifying Agent Prompts

Agent system prompts are in `prompt-templates/`:
- `pom_builder.md.j2` - Page Object generation
- `test_writer.md.j2` - Test writing
- `healer.md.j2` - Failure fixing

Edit Jinja2 templates to adjust agent behavior.

## License

See LICENSE file for details.

## Support

For issues and feature requests, see the issue tracker.
