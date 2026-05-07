# OpenProject DOM Quirks — Runtime Behavior Only

This file contains ONLY runtime behavior that cannot be discovered by reading source code.
For element IDs, CSS classes, and attributes, read the Rails source code instead (see source-code-map.md).

## Board Module

- `#add-board-button` exists TWICE in DOM (text version + icon-only mobile version). Use `#add-board-button[aria-label="Create new board"]` to select uniquely.
- Board delete links are `<a title="Delete">` (not `<button>`). Use `locator('[title="Delete"]')`.
- Turbo DELETE follows 302 redirect as DELETE → 404. Fix: capture URL before deletion, wait for 302 response, then `page.goto(savedUrl)`.
- When all boards deleted, `table.generic-table` disappears entirely (no empty table). `getNumberOfRows()` must check `rootLocator.count() === 0` first.
- `getByRole('link', { name: 'Boards' })` resolves to 2 elements on board view. Use `locator('#content-body').getByRole('link', { name: 'Boards' })`.
- "Delete all boards" test needs `test.setTimeout(180_000)` — 10+ boards × ~5s each exceeds 30s default.

## Members Module

- After invite, `page.reload()` must be called TWICE for the member list to update reliably.
- BOTH the ALL members list AND the Invited view have pagination (20 per page). After navigating to Invited sidebar, click "Show 100 per page" link if visible. Set `test.setTimeout(60_000)` for member tests.
- `getByRole('combobox', { name: 'Search' })` resolves to 2 elements (global search bar + member invite search). MUST scope to `#members_add_form`.
- `getByRole('button', { name: 'Add' })` resolves to 3 elements (header quick-add, add-member toggle, submit). Use `#add-member--submit-button` instead.
- `getByRole('button', { name: 'Actions' })` fails on member rows — the accessible name comes from a tooltip `aria-labelledby` that may not render. Use `button[aria-haspopup="true"]` within the row scope.
- `getByRole('link', { name: 'Invited' })` causes strict mode violation. Use `[data-test-selector="op-submenu--item-action"][href*="status=invited"]`.
- Delete confirmation dialog starts hidden (CSS animation on `spot-modal-overlay`). Use `waitFor({ state: 'attached' })`, NOT `waitFor()` which defaults to visible. Click danger button with `dispatchEvent('click')`.
- After member removal, explicitly navigate back with `page.goto(membersUrl)` — the page does not auto-redirect.
- `isMemberWithEmailVisible` must use auto-wait pattern (`.waitFor({ timeout })`), NOT manual loop with `count()` + `textContent()`.
