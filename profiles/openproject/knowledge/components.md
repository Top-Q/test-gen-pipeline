# Component Pattern

## Base Class

```typescript
// src/po/openproject/baseComponent.ts
import { Page, Locator } from '@playwright/test';
import { BasePage } from '../../../internals';

export abstract class BaseComponent<T = unknown> extends BasePage<T> {
    constructor(protected page: Page, protected readonly rootComponent: Locator) {
        super(page);
    }

    protected self<U extends BaseComponent<U>>(u: U): U {
        return u;
    }
}
```

## When to Use Components vs Pages

- **Page**: Represents a full navigable screen with a URL (e.g., login page, work packages list)
- **Component**: Represents a reusable UI section within a page (e.g., sidebar menu, dropdown, dialog, table, table row)

## Creating a New Component

```typescript
// src/po/openproject/<subdirectory>/<componentName>Comp.ts
import { Locator, Page } from '@playwright/test';
import { BaseComponent, NewWorkpackagePage } from '../../../internals';

/**
 * Dropdown menu that appears when creating a new work package.
 */
export class TaskTypeMenu extends BaseComponent<TaskTypeMenu> {

    private readonly taskMenuItem: Locator;
    private readonly milestoneMenuItem: Locator;

    constructor(readonly page: Page) {
        // Pass the root element that scopes this component
        super(page, page.locator('.dropdown-relative').describe('Task Type Menu'));
        // Locators are scoped to rootComponent, not the full page
        this.taskMenuItem = this.rootComponent.getByRole('menuitem', { name: 'Task', exact: true }).describe('Task menu item');
        this.milestoneMenuItem = this.rootComponent.getByRole('menuitem', { name: 'Milestone' }).describe('Milestone menu item');
    }

    async waitForLoad(): Promise<TaskTypeMenu> {
        await this.rootComponent.first().waitFor();
        return this;
    }

    async clickTaskMenuItem(): Promise<NewWorkpackagePage> {
        await this.taskMenuItem.click();
        return new NewWorkpackagePage(this.page);
    }
}
```

## Key Differences from Pages

1. Constructor takes an additional `rootComponent: Locator` parameter (via `super()`)
2. Child locators are scoped to `this.rootComponent` instead of `this.page`
3. Components are typically instantiated by pages, not by tests directly
4. Components don't have `goto()` methods — they appear as part of a page interaction
5. Component class names use the `Comp` suffix (e.g., `MainMenuComp`, `ProjectSelectionComp`)

## Component with Dynamic Root

When a component's root depends on runtime data (e.g., a specific table row):

```typescript
export class WorkPackageRow extends BaseComponent<WorkPackageRow> {
    constructor(readonly page: Page, readonly locator: Locator) {
        super(page, locator);
    }

    async getSubject(): Promise<string> {
        return await this.rootComponent.locator('.subject').textContent() ?? '';
    }
}
```
