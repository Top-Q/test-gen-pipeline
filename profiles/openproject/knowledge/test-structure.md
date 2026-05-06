# Test Structure

## File Organization

- UI tests live in `tests/ui/<component>/` — one subdirectory per component (e.g. `tests/ui/members/`, `tests/ui/boards/`)
- API tests live in `tests/api/`
- Test files use `.spec.ts` extension with kebab-case names (e.g. `members-crud.spec.ts`)
- Import `test` from `'../fixtures'` (the shared fixture at `tests/ui/fixtures.ts`)
- Import `expect` from `@playwright/test`
- Import page objects from `'../../../internals'` (three levels up from `tests/ui/<component>/` to the project root)

**Important:** Import paths depend on nesting depth. From `tests/ui/members/members-crud.spec.ts`:
- `test` fixture: `import { test } from '../fixtures'`
- Page objects: `import { MembersPage } from '../../../internals'`

## Test Template

```typescript
import { expect } from '@playwright/test';
import { test } from './fixtures';
import { WorkPackagesPage } from '../../internals';

test.describe('Work Packages', () => {
    test('should create a new task', { tag: ['@ui', '@task', '@regression'] },
        async ({ readyOverviewPage }) => {

        let workPackagesPage: WorkPackagesPage;

        await test.step('Given user navigates to work packages page', async () => {
            workPackagesPage = await readyOverviewPage.mainMenu().clickWorkPackagesLink();
        });

        const taskName = `Auto Task ${Date.now()}`;

        await test.step(`When user creates a new task "${taskName}"`, async () => {
            const taskTypeMenu = await workPackagesPage.clickCreateButton();
            const newTaskPage = await taskTypeMenu.clickTaskMenuItem();
            await newTaskPage.fillSubject(taskName);
            await newTaskPage.clickSaveButton();
        });

        await test.step('Then the task appears in the work packages table', async () => {
            const table = await workPackagesPage.workPackageTable();
            const exists = await table.isWorkPackageBySubjectExists(taskName);
            expect(exists).toBe(true);
        });
    });
});
```

## Step Structure (Given/When/Then)

Every test uses `test.step()` with BDD-style descriptions:

- **Given** — preconditions and setup within the test
- **When** — the action being tested
- **Then** — assertions and expected outcomes
- **And** — continuation of the current phase

Steps appear in the HTML report and traces, making failures easy to locate.

## Key Rules

1. **Assertions live in tests only** — use `expect()` in test steps, never in page objects
2. **Use locator getters** — call `page.getHeading()` then `expect(...)` on the result
3. **One concern per step** — each step does one logical thing
4. **Dynamic data in step names** — interpolate values for traceability:
   ```typescript
   await test.step(`When user creates a project named "${projectName}"`, async () => {
   ```
5. **Fixture for auth** — authenticated tests use `readyOverviewPage` fixture, not `beforeEach`
6. **Tags for filtering** — use tags when tests belong to categories:
   ```typescript
   test('create task', { tag: ['@ui', '@task', '@regression'] }, async ({ ... }) => {
   ```
7. **Test isolation** — each test is self-contained, creates its own data, cleans up if needed

## Test Grouping

Use `test.describe()` to group related tests:

```typescript
test.describe('Work Packages CRUD', () => {
    test('should create a task', async ({ readyOverviewPage }) => { ... });
    test('should edit a task', async ({ readyOverviewPage }) => { ... });
    test('should delete a task', async ({ readyOverviewPage }) => { ... });
});
```
