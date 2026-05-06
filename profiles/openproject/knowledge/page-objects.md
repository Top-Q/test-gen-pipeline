# Page Object Pattern

## Base Class

```typescript
// src/po/openproject/basePage.ts
import { Page } from '@playwright/test';

export abstract class BasePage<T = unknown> {
    constructor(protected readonly page: Page) {}

    async waitForLoad(): Promise<T> {
        await this.page.waitForLoadState('load');
        return this as unknown as T;
    }
}
```

## Creating a New Page Object

Every page object follows this template:

```typescript
// src/po/openproject/<subdirectory>/<pageName>Page.ts
import { Locator, Page } from '@playwright/test';
import { BasePage, SomeOtherPage } from '../../../internals';

/**
 * Brief description of what this page represents.
 */
export class ExamplePage extends BasePage<ExamplePage> {

    private readonly heading: Locator;
    private readonly submitButton: Locator;
    private readonly nameInput: Locator;

    constructor(public readonly page: Page) {
        super(page);
        this.heading = this.page.getByRole('heading', { name: 'Example' }).describe('Example page heading');
        this.submitButton = this.page.getByRole('button', { name: 'Submit' }).describe('Submit button');
        this.nameInput = this.page.getByRole('textbox', { name: 'Name' }).describe('Name input');
    }

    async waitForLoad(): Promise<ExamplePage> {
        await this.heading.waitFor({ state: 'visible' });
        return this;
    }

    // Locator getters for test assertions
    getHeading(): Locator {
        return this.heading;
    }

    // Action methods
    async fillName(name: string): Promise<void> {
        await this.nameInput.fill(name);
    }

    // Navigation methods return the destination page
    async clickSubmit(): Promise<SomeOtherPage> {
        await this.submitButton.click();
        return await new SomeOtherPage(this.page).waitForLoad();
    }
}
```

## Checklist for New Page Objects

1. Extends `BasePage<ClassName>`
2. Constructor calls `super(page)` and initializes all locators
3. All locators are `private readonly` with `.describe()`
4. `waitForLoad()` overridden to wait for a key visible element
5. Getter methods for locators that tests need to assert against
6. Navigation methods return the next page object instance
7. No `expect` imports — assertions stay in tests
8. Exported from `internals.ts`

## File Placement

Page objects go in the appropriate subdirectory under `src/po/openproject/`:
- `general/` — common pages (login, home, overview, main menu, project selection)
- `workpackage/` — work package related pages
- `board/` — board related pages
- Create new subdirectories for new feature areas
