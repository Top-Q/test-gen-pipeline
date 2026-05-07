# Knowledge Files & Test Plans

## Updating knowledge files

If you identify patterns that should be captured for future runs, update the relevant knowledge files.

### When to update which file

| Knowledge file | When to update |
|----------------|----------------|
| `dom-quirks.md` | Discovered new DOM behavior (dynamic IDs, shadow DOM, timing issues, loading states) |
| `locator-patterns.md` | Found better locator strategies for specific UI patterns |
| `source-code-map.md` | New pages/components were created; new source code paths discovered |
| `failure-patterns.md` | Recurring failure pattern that agents should know about |
| `page-objects.md` | PO architecture pattern needs clarification or new example |
| `components.md` | Component architecture pattern needs clarification or new example |
| `test-structure.md` | Test writing conventions need updates |
| `module-scaffold.md` | Module creation checklist needs new steps |
| `browser-tools.md` | playwright-cli usage patterns need updates |

### File locations

- **Shared (all profiles):** `profiles/_base/knowledge/`
- **Profile-specific:** `profiles/<name>/knowledge/` (overrides _base by filename stem)

### How merging works

1. All `.md` files in `_base/knowledge/` are loaded (stem name = role key)
2. Profile-specific files with the same stem override the base version
3. Explicit entries in `knowledge_files:` in profile.yaml take highest priority

### Guidelines for updating

- Keep files focused on their role — don't mix locator patterns into dom-quirks
- Use concrete examples from actual failures or discoveries
- Include the module/page context so agents know when the pattern applies
- For `source-code-map.md`: update whenever new PO directories are created, new ERB/component paths are discovered, or element ID conventions change
- For `dom-quirks.md`: include the exact element behavior, not just "it's flaky" — describe timing, dynamic content, or state-dependent rendering
- For `failure-patterns.md`: include the error message pattern, root cause, and the fix that worked

## Creating a test plan

Test plans use YAML frontmatter + Gherkin syntax, with `---` separating multiple scenarios.

### Format

```markdown
---
id: TEST-001
suite: MySuite
feature: Feature Name
component: module_name
priority: P1
tags: [ui, regression]
variables:
  itemName: "test-item-<uuid4>"
setup:
  - create_item: { name: "{{ itemName }}" }
---

Background:
  Given the user is authenticated as "default"
  And the user is on the Feature page

Scenario: Create a new item
  When the user creates a new item with name "<itemName>"
  Then the item appears in the list with name "<itemName>"

---
id: TEST-002
suite: MySuite
feature: Feature Name
component: module_name
priority: P2
tags: [ui]
variables:
  itemName: "delete-me-<uuid4>"
setup:
  - create_item: { name: "{{ itemName }}" }
---

Background:
  Given the user is authenticated as "default"
  And the user is on the Feature page

Scenario: Delete an existing item
  When the user deletes the item with name "<itemName>"
  Then the item no longer appears in the list
```

### Field reference

| Field | Required | Description |
|-------|----------|-------------|
| `id` | Yes | Unique test identifier (e.g. `TEST-001`) |
| `suite` | Yes | Suite grouping name |
| `feature` | Yes | Feature being tested |
| `component` | Yes | Maps to PO directory: `src/po/openproject/<component>/` |
| `priority` | No | P1, P2, P3 (default: P3) |
| `tags` | No | List of tags for filtering (e.g. `[ui, regression]`) |
| `variables` | No | Key-value pairs; `<uuid4>` generates unique values at runtime |
| `setup` | No | API preconditions to execute before the test |

### Guidelines

- One scenario per YAML document (separated by `---`)
- `component` must match the PO directory name — the pipeline uses it to check if POs exist
- Group related scenarios (same component) in one plan file
- Background section defines shared preconditions for the scenario
- Steps use standard Gherkin keywords: Given, When, Then, And, But
- Keep scenarios focused on one behavior each
- If a test deletes an entity, include a `setup` step that creates it

## Configuring a profile

### Creating a new profile

1. Create directory: `profiles/<name>/`
2. Create `profiles/<name>/profile.yaml` with required fields
3. Optionally create `profiles/<name>/knowledge/` with `.md` files

### Profile YAML template

```yaml
name: my-project
stack: react                     # rails/angular/react/vue/nextjs
project_root: "/path/to/project" # Absolute path, must exist
po_base_dir: src/po/my-project   # Relative to project_root
test_dir: tests/ui               # Relative to project_root
barrel_export: internals.ts      # Relative to project_root (optional, null to skip)
fixture_path: tests/ui/fixtures.ts  # Relative to project_root, must exist
base_url: "http://localhost:3000"
auth:
  strategy: session_cookie       # session_cookie, api_key, basic
  username: admin
  password: admin
validation:
  lint_command: "npx eslint {files}"    # {files} is replaced with file paths
  typecheck_command: "npx tsc --noEmit" # Runs project-wide
  structural_checks: []                 # Optional regex checks
knowledge_files: {}                     # Optional explicit role→path overrides
```

### Structural checks

Add regex-based validation rules:

```yaml
structural_checks:
  - name: no-expect-in-po
    pattern: "import.*expect.*from.*@playwright/test"
    file_glob: "src/po/**/*.ts"
    must_match: false        # Pattern must NOT exist
    error_message: "Page objects must not import expect"
  - name: waitforload-exists
    pattern: "async waitForLoad\\("
    file_glob: "src/po/**/*.ts"
    must_match: true         # Pattern MUST exist
    error_message: "Every page/component must implement waitForLoad()"
```
