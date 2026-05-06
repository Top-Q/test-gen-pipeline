# OpenProject DOM Quirks

## Board Module
- `#add-board-button` exists TWICE in DOM (text version + icon-only mobile version). Use `#add-board-button[aria-label="Create new board"]` to select uniquely.
- Board delete links are `<a title="Delete">` (not `<button>`). Use `locator('[title="Delete"]')` in `BoardTableRowComp`.
- Turbo DELETE follows 302 redirect as DELETE → 404. Fix: capture URL before deletion, wait for 302 response, then `page.goto(savedUrl)`.
- When all boards deleted, `table.generic-table` disappears entirely (no empty table). `getNumberOfRows()` must check `rootLocator.count() === 0` first.
- Board creation flow changed: `boards/new` is now a combined form (Title + type radio + Create button). No separate type-selection page.
- `getByRole('link', { name: 'Boards' })` resolves to 2 elements on board view. Use `locator('#content-body').getByRole('link', { name: 'Boards' })`.
- "Delete all boards" test needs `test.setTimeout(180_000)` — 10+ boards × ~5s each exceeds 30s default.

## Navigation Patterns
- `BasePage.waitForLoad()` returns `this as T`, enabling chaining. ALL navigation methods that return a new page/component MUST chain `.waitForLoad()`.
- Tests MUST NOT call `await page.waitForLoad()` after a navigation method — it's already done inside the PO.

## Circular Dependencies
- When `mainMenuComp.ts` imports a new page directly, that page's PO files MUST import `BasePage`/`BaseComponent` from source, NOT from `internals.ts`.
- `mainMenuComp.ts` already imports `MembersPage` from `'../members/membersPage'` and `WorkPackagesPage` from `'../workpackage/workPackagesPage'`. Do NOT modify `mainMenuComp.ts` — just create the corresponding page class with the correct export name and `waitForLoad()` method.

## Members Module

**Add member form** (`#members_add_form`):
- Opened by clicking the "Add member" button (`getByRole('button', { name: 'Add member' })`)
- Role is selected FIRST via `#member_role_ids` select element (`selectOption({ label: role })`)
- User/email search is a combobox: type into `#members_add_form` → `getByRole('combobox', { name: 'Search' })`
- Matching options appear in `.ng-dropdown-panel .ng-option` — filter by text and click `.first()`
- After clicking Add: wait for POST response to URL containing `/members`, then call `page.reload()` twice

**CRITICAL — After invite, navigate to "Invited" view before interacting with the member row**:
The ALL members list can have pagination with 50+ accumulated test members. A newly invited member may not appear on page 1. Do NOT call `getMemberRowByEmail(email)` on the unfiltered view. Instead, always click the "Invited" sidebar link first:
```typescript
// CORRECT:
await inviteDialog.inviteMember(email, role);
await membersPage.clickInvitedMembersLink(); // navigate to invited-only view
const memberRow = membersPage.getMemberRowByEmail(email); // now guaranteed visible

// WRONG — member may be on page 2 of the all-members list:
// await inviteDialog.inviteMember(email, role);
// const memberRow = membersPage.getMemberRowByEmail(email); // times out!
```

**`isMemberWithEmailVisible` — use Playwright auto-wait instead of manual loop**:
Manual loops with `count()` don't auto-retry and return false if table is still loading. Use `expect().toBeVisible()` pattern:
```typescript
// CORRECT — auto-waits with retry:
async isMemberWithEmailVisible(email: string): Promise<boolean> {
    const memberRow = this.getMemberRowByEmail(email);
    try {
        await expect(memberRow.getEmailCell()).toBeVisible({ timeout: 10000 });
        return true;
    } catch {
        return false;
    }
}

// WRONG — no auto-retry, fails if table is loading:
// const count = await emailLinks.count();
// for (let i = 0; i < count; i++) { ... }
```

**Filter panel** (IMPORTANT — wrong names cause timeouts):
- Filter toggle button is named `'Filter'`, NOT `'Activate filter'`. Use `getByRole('button', { name: 'Filter' })`.
- After clicking Filter, check for the name input: `getByRole('textbox', { name: /Name/ })`
- Apply button: `getByRole('button', { name: 'Apply' })`, Clear: `getByRole('button', { name: 'Clear' })`

**Sidebar navigation** (IMPORTANT — strict mode violation risk):
- Sidebar links for `All`, `Locked`, `Invited` are `<a>` elements with `data-test-selector="op-submenu--item-action"`.
- Do NOT use `getByRole('link', { name: 'Invited' })` — this matches member name links too (strict mode violation).
- Use URL-based locators: `locator('[data-test-selector="op-submenu--item-action"][href*="status=invited"]')` for "Invited".
- Similarly: `[href*="status=locked"]` for Locked; omit the status query param for "All".

**`MembersPage.waitForLoad()`** — wait for the "Add member" button, NOT a heading:
```typescript
async waitForLoad(): Promise<MembersPage> {
    await this.addMemberButton.waitFor();
    return this;
}
```
Do NOT wait for `getByRole('heading', { name: /members/i })` — the heading text changes in filtered views.

**Filter panel** — wait for the Apply button, NOT a CSS class:
```typescript
// Open filter
await this.filterButton.click();   // filterButton = getByRole('button', { name: 'Filter' })
await this.page.getByRole('button', { name: 'Apply' }).waitFor();
// Filter by name
await this.page.getByRole('textbox', { name: /Name/ }).fill(name);
await this.page.getByRole('button', { name: 'Apply' }).click();
await this.page.waitForLoadState('load');
```
Do NOT use CSS classes like `.filter-panel` or `.advanced-filters--form` — they don't exist.

**`MembersPage` row API** — CRITICAL: Do NOT create a `memberTable()` method that returns `MemberTableRowComp(page, tableLocator)` with the whole table as root. This causes every row interaction to match ALL rows (20+ strict mode violations). The ONLY correct API is:
```typescript
// CORRECT — scoped to a specific row:
getMemberRowByEmail(email: string): MemberTableRowComp {
    const rowLocator = this.memberTableRoot
        .locator('tbody tr')
        .filter({ has: this.page.locator('td.email a').getByText(email, { exact: true }) });
    return new MemberTableRowComp(this.page, rowLocator);
}

// WRONG — DO NOT create this method:
// memberTable(): MemberTableRowComp {
//     return new MemberTableRowComp(this.page, this.memberTableRoot); // BROKEN: whole table as root
// }
```
Tests must ALWAYS call `getMemberRowByEmail(email)` to get a row for actions. Never call a method that wraps the whole table.

**`isMemberWithEmailVisible` — wait for table before checking**:
After invite + reload, wait for the table to settle before checking visibility:
```typescript
async isMemberWithEmailVisible(email: string): Promise<boolean> {
    // Wait for at least one row to appear (table may still be loading after reload)
    const tableRows = this.page.locator('table.generic-table tbody tr');
    await tableRows.first().waitFor({ timeout: 10000 }).catch(() => {}); // ignore if no rows
    const emailLinks = this.page.locator('table.generic-table td.email a');
    const count = await emailLinks.count();
    for (let i = 0; i < count; i++) {
        const text = await emailLinks.nth(i).textContent();
        if (text?.trim() === email) return true;
    }
    return false;
}
```

**Member table row** — CRITICAL: ALL locators in `MemberTableRowComp` MUST be scoped to `this.rootComponent` (the `<tr>` element), NOT to `this.page` or `locator('table.generic-table')`:
```typescript
// CORRECT — scoped to the row, using aria-haspopup (NOT getByRole name which relies on tooltip rendering):
private readonly actionsButton = this.rootComponent
    .locator('button[aria-haspopup="true"]')
    .describe('Row actions menu');

// WRONG — getByRole name matching fails when tooltip element isn't in DOM:
// this.rootComponent.getByRole('button', { name: 'Actions' })
// this.page.getByRole('button', { name: 'Actions' })
// locator('table.generic-table').getByRole('button', { name: 'Actions' })
```
- Context menu button: `this.rootComponent.locator('button[aria-haspopup="true"]')` — the Actions button uses GitHub Primer popover with `aria-haspopup="true"`. Use CSS attribute selector, NOT `getByRole` with name (the accessible name comes from an `aria-labelledby` tooltip that may not be rendered, causing name matching to fail).
- After clicking "Manage roles", wait for: `this.rootComponent.getByRole('button', { name: 'Change' })` (NOT a global checkbox - those are hidden)
- Toggle roles: `this.rootComponent.getByRole('checkbox', { name: roleName })`
- Remove member: Primer dialog with `a.Button--danger` — use `dispatchEvent('click')` NOT `.click()`
- Remove confirmation dialog: `[role="dialog"]` uses `spot-modal-overlay` class that starts hidden (CSS animation). Use `{ state: 'attached' }` not default `visible`:
  ```typescript
  const confirmDialog = this.page.locator('[role="dialog"]');
  await confirmDialog.waitFor({ state: 'attached' }); // NOT just waitFor() which waits for visible
  const removeButton = confirmDialog.locator('a.Button--danger');
  await removeButton.dispatchEvent('click');
  ```
- After removal: navigate back explicitly via `page.goto(membersUrl)`
- Name: `this.rootComponent.locator('td.name a')`, Email: `td.email a`, Roles: `td.roles`, Status: `td.status`

## Work Package Module — Required Classes
The work package module MUST expose these classes via `internals.ts` (other tests depend on them):
- `WorkPackagesPage` — the WP list page (`/projects/<id>/work_packages`)
- `WorkPackageDetailPage` — the detail/edit view for a single WP (used by `tests/ui/time-and-costs/time-and-costs.spec.ts`)

When running `npx tsc --noEmit`, you MUST fix ALL errors — including errors in files you did NOT create (e.g. `tests/seed.spec.ts`, `tests/ui/time-and-costs/`). Those files may import old work-package class names that no longer exist; update their imports to use the new class names you created.
