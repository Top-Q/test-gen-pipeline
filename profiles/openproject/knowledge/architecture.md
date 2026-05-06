---
name: architecture
description: Generates page objects, components, fixtures, and tests following the project's established architecture patterns. Use when the user needs to create new page objects, add components, create fixtures, or scaffold test infrastructure.
---

# Project Architecture Skill

Use this skill when creating or modifying page objects, components, fixtures, or tests in this Playwright project.

## Project Structure

```
<project-root>/
├── src/po/openproject/           # Page objects and components
│   ├── basePage.ts               # Abstract base for all pages
│   ├── baseComponent.ts          # Abstract base for all components
│   ├── general/                  # Login, home, overview, main menu, project selection
│   ├── workpackage/              # Work package pages and components
│   └── board/                    # Board pages and components
├── src/api/                      # Fluent API client
├── tests/
│   ├── ui/                       # UI tests + fixtures.ts
│   │   └── <feature>/            # Feature subdirectories
│   └── api/                      # API tests + fixtures.ts
├── internals.ts                  # Central barrel export (all imports go through here)
├── tsconfig.json
└── playwright.config.ts
```

## Architecture Rules

### 1. All page objects extend `BasePage<T>`

Every page object must extend `BasePage` with its own type as the generic parameter. This enables type-safe fluent method chaining.

See: [references/page-objects.md](references/page-objects.md)

### 2. All components extend `BaseComponent<T>`

Components represent reusable UI parts scoped to a root element (e.g., menus, dialogs, tables). They extend `BaseComponent` which adds a `rootComponent` locator.

See: [references/components.md](references/components.md)

### 3. Assertions belong in tests, NOT in page objects

Page objects expose locator getters (e.g., `getHeading(): Locator`) so tests can assert against them. Page objects never import `expect`.

### 4. All imports go through `internals.ts`

Every new page object or component must be exported from `internals.ts`. All imports in page objects and tests use the relative path to `internals.ts` (e.g., `../../../internals` from POs, `../../internals` from tests).

### 5. Use Playwright fixtures for test setup

Authentication and navigation setup goes in `tests/ui/fixtures.ts` or `tests/api/fixtures.ts`, not in `beforeEach` hooks.

See: [references/fixtures.md](references/fixtures.md)

### 6. Use `test.step()` for structured test logging

Tests use Given/When/Then step structure for readability and HTML report clarity.

See: [references/test-structure.md](references/test-structure.md)

### 7. Locators use `.describe()` for trace clarity

All locators should have `.describe('Description')` appended for better debugging in traces and reports.

### 8. Locators are `private readonly`

Page objects expose locators through getter methods, not public properties. This maintains encapsulation.

### 8b. Follow locator best practices

Prefer `getByRole()` over CSS selectors. Scope locators to containers when the same text appears in multiple areas.

See: [references/locator-patterns.md](references/locator-patterns.md)

### 9. Navigation methods return the next page object

Methods that cause navigation return an instance of the destination page (fluent pattern). Call `waitForLoad()` on the returned instance.

### 10. Every page/component implements `waitForLoad()`

Override `waitForLoad()` to wait for a key element that confirms the page/component is ready.

### 11. Module Scaffolding

When creating page objects for an entirely new module, follow the module scaffold checklist.

See: [references/module-scaffold.md](references/module-scaffold.md)
