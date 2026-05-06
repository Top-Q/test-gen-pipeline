# Module Scaffold Checklist

Follow this checklist when creating page objects for an entirely new OpenProject module.

## Prerequisites

Run the **investigate-module** skill first to produce a structured investigation report. You need:
- List of pages and their URL patterns
- List of components (dialogs, tables, forms)
- Key load indicators for each page/component
- DOM quirks to account for
- The main menu link selector

The investigate-module skill will use **source code** (preferred) if available at the matching version, or **live browser investigation** otherwise. Source code investigation produces more accurate locators upfront and requires fewer debug iterations.

## Directory Structure

```
src/po/openproject/<module>/       # lowercase, no hyphens (e.g., timeandcosts)
├── <page1>Page.ts
├── <page2>Page.ts
└── <component>Comp.ts

tests/ui/<module>/                 # matches PO directory name when possible
├── fixtures.ts
└── <feature>.spec.ts
```

## Step-by-Step

### 1. Create the PO directory

```
src/po/openproject/<module>/
```

Naming: lowercase, no hyphens. Examples: `workpackage`, `board`, `timeandcosts`.

### 2. Create page objects (one per page)

Each page object must:
- Extend `BasePage<T>` with its own type as generic parameter
- Implement `waitForLoad()` using the key load element from the investigation report
- Define all locators as `private readonly` with `.describe()`
- Expose locators via getter methods
- Return destination POs from navigation methods (fluent pattern)
- Chain `.waitForLoad()` on all returned POs

Follow the template in [page-objects.md](page-objects.md).

### 3. Create components (one per dialog/table/section)

Each component must:
- Extend `BaseComponent<T>` with its own type as generic parameter
- Accept a `rootComponent` locator scoping all internal locators
- Implement `waitForLoad()`

Follow the template in [components.md](components.md).

### 4. Update MainMenuComp

Add a locator and navigation method for the new module's sidebar link:

```typescript
private readonly <module>Link = this.rootComponent
    .getByRole('link', { name: '<Menu Text>' })
    .describe('<Module> menu link');

async click<Module>Link(): Promise<<LandingPage>> {
    await this.<module>Link.click();
    return await new <LandingPage>(this.page).waitForLoad();
}
```

Import the landing page PO **directly from its file** (not through `internals.ts`) to avoid circular dependency issues:

```typescript
import { <LandingPage> } from '../<module>/<landingPage>Page';
```

### 5. Update internals.ts

Add exports for all new POs and components, grouped under a comment header:

```typescript
// <Module Name>
export * from './src/po/openproject/<module>/<page1>Page';
export * from './src/po/openproject/<module>/<page2>Page';
export * from './src/po/openproject/<module>/<component>Comp';
```

### 5b. Fix circular dependency in new module PO files

Because `MainMenuComp` imports the new module's landing page directly (step 4), and `MainMenuComp` is exported via `internals.ts`, any new module PO that imports from `internals.ts` creates a circular chain:

```
internals → mainMenuComp → <newPage> → internals
```

This causes the TypeScript language server to report **"Unsafe assignment of an error typed value"** in tests.

**Fix:** In all new module PO files, import `BasePage` and `BaseComponent` directly from their source files — **not** from `internals.ts`:

```typescript
// DO THIS in new module PO files:
import { BasePage } from '../basePage';
import { BaseComponent } from '../baseComponent';

// NOT THIS:
import { BasePage } from '../../../../internals';
import { BaseComponent } from '../../../../internals';
```

This applies to every `.ts` file under `src/po/openproject/<module>/`.

### 6. Create the test directory and fixtures

```
tests/ui/<module>/fixtures.ts
```

The fixture file extends the base test with module-specific page setup.

### 7. Lint all new files

```bash
npx eslint src/po/openproject/<module>/*.ts tests/ui/<module>/*.ts internals.ts
```

Fix all errors before finishing.

## Common Module Patterns

| Pattern | Description | Example |
|---------|-------------|---------|
| **List/Detail** | Landing page shows a list/table, clicking a row opens a detail page | Work Packages |
| **Settings/Report** | Page with filters/settings that generates a report view | Time and Costs |
| **Board/Kanban** | Board listing page → individual board with columns/cards | Boards |

Identify which archetype your module follows — it guides how many POs you need and what navigation methods to create.

## Cross-Module Dependencies

Some navigation methods return POs from other modules (e.g., a work package link on a board card). When this happens:
- Import the target PO directly from its file, not through `internals.ts`
- This avoids circular dependency chains through the barrel export
- Document the cross-module dependency in a code comment
