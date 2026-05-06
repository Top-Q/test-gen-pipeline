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
- Role selected FIRST via `#member_role_ids` (`selectOption({ label: role })`)
- User search: `getByRole('combobox', { name: 'Search' })`, options in `.ng-dropdown-panel .ng-option`
- After Add: wait for POST to `/members`, then `page.reload()` twice

**After invite, ALWAYS navigate to "Invited" view** before interacting with member rows or checking visibility. The ALL members list has pagination — newly invited members may not be on page 1.

**`isMemberWithEmailVisible`** — use auto-wait, NOT manual loop:
```typescript
async isMemberWithEmailVisible(email: string): Promise<boolean> {
    try {
        await this.getMemberRowByEmail(email).getEmailCell().waitFor({ timeout: 10000 });
        return true;
    } catch { return false; }
}
```

**Filter panel**: button is `'Filter'` (NOT `'Activate filter'`). Wait for `getByRole('button', { name: 'Apply' })`. Do NOT use CSS classes `.filter-panel` or `.advanced-filters--form`.

**Sidebar**: Use `[data-test-selector="op-submenu--item-action"][href*="status=invited"]` for Invited. Do NOT use `getByRole('link', { name: 'Invited' })` — strict mode violation.

**`waitForLoad()`**: wait for `addMemberButton`, NOT a heading.

**Row API**: `getMemberRowByEmail(email)` scoped to `tbody tr` filtered by email. Do NOT create `memberTable()` returning whole table as root.

**`MemberTableRowComp` locators** — ALL scoped to `this.rootComponent`:
- Actions button: `this.rootComponent.locator('button[aria-haspopup="true"]')` — do NOT use `getByRole('button', { name: 'Actions' })` (tooltip-based accessible name may not resolve)
- After "Manage roles": wait for `this.rootComponent.getByRole('button', { name: 'Change' })`
- Toggle roles: `this.rootComponent.getByRole('checkbox', { name: roleName })`
- Remove dialog: `page.locator('[role="dialog"]')` with `waitFor({ state: 'attached' })` (NOT visible — CSS animation). Then `confirmDialog.locator('a.Button--danger').dispatchEvent('click')`
- After removal: `page.goto(membersUrl)` explicitly

## Work Package Module — Required Classes
The work package module MUST expose these classes via `internals.ts` (other tests depend on them):
- `WorkPackagesPage` — the WP list page (`/projects/<id>/work_packages`)
- `WorkPackageDetailPage` — the detail/edit view for a single WP (used by `tests/ui/time-and-costs/time-and-costs.spec.ts`)

When running `npx tsc --noEmit`, you MUST fix ALL errors — including errors in files you did NOT create (e.g. `tests/seed.spec.ts`, `tests/ui/time-and-costs/`). Those files may import old work-package class names that no longer exist; update their imports to use the new class names you created.
