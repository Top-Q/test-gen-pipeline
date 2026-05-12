# Browser Investigation with playwright-cli

## Purpose

Before writing or fixing locators, inspect the **live DOM** using `playwright-cli`.
Text-based source code analysis alone cannot predict runtime quirks, dynamic IDs,
or strict-mode ambiguities. Always verify against the real page.

## Quick Reference

| Command | Description |
|---------|-------------|
| `playwright-cli open` | Launch a browser instance |
| `playwright-cli goto <url>` | Navigate to a URL |
| `playwright-cli snapshot` | Capture the full ARIA accessibility tree |
| `playwright-cli snapshot --depth=N` | Capture ARIA tree limited to depth N |
| `playwright-cli fill <selector> <value>` | Fill an input field |
| `playwright-cli click <selector>` | Click an element |
| `playwright-cli press <key>` | Press a keyboard key (e.g. `Enter`, `Escape`, `Tab`) |
| `playwright-cli eval <js-expression>` | Evaluate JavaScript in the page |
| `playwright-cli state-save <file>` | Save browser auth/session state to a JSON file |
| `playwright-cli state-load <file>` | Load saved auth state (skip login) |
| `playwright-cli close` | Close the browser |

Add `--raw` to any command to get unformatted output (useful for piping/parsing).

**IMPORTANT:** The `<selector>` in `click`/`fill` accepts CSS selectors. Do NOT use snapshot `ref=eN` values as selectors — they are ARIA tree references only, not CSS selectors.

**NOTE:** Some Angular overlays (dropdowns, menus) do NOT appear in the ARIA snapshot. Use `playwright-cli eval "document.querySelectorAll('[role=menuitem]').length"` to confirm elements exist, and use `getByRole` in Playwright code — it can find them even when they're in overlays.

## Authentication Helper

Most pages require login. Credentials and base URL come from the profile (see "Profile credentials" section in this prompt).

```bash
playwright-cli goto <BASE_URL>/login
playwright-cli fill '#username' '<AUTH_USERNAME>'
playwright-cli fill '#password' '<AUTH_PASSWORD>'
playwright-cli press 'Enter'
```

Wait for navigation to complete, then save the session so you don't need to log in again:

```bash
playwright-cli state-save .playwright-cli/auth.json
```

To reuse on subsequent runs:
```bash
playwright-cli state-load .playwright-cli/auth.json
playwright-cli goto <BASE_URL>
```

## Workflow: POM Builder

The browser is the **only** source of truth for locators. Do not derive locators from source code and then try to reconcile them with the snapshot — this leads to hallucinated mappings. Source code tells you where to navigate and what the app does; the snapshot tells you what to click.

1. `playwright-cli open` — launch browser
2. Log in using the auth helper above
3. `playwright-cli goto <module-page-url>` — navigate to the page you are building POs for
4. `playwright-cli snapshot` — capture the ARIA tree
5. Identify the interactive elements you need: look for their **role** and **accessible name** in the snapshot (e.g., `button "Add member" [ref=e165]`)
6. Write the locator using what the snapshot shows:
   - Unique accessible name → `getByRole('button', { name: 'Add member' })`
   - No unique name → find a stable element ID using `playwright-cli eval "document.querySelector('.some-class').id"` then use `#id`
7. **Do not guess element IDs from source code filenames or component names.** If you suspect an ID exists, verify it: `playwright-cli eval "document.querySelector('#suspected-id') ? 'found' : 'missing'"`
8. For elements not visible in the ARIA snapshot (Angular overlays, CDK portals): use `playwright-cli eval "document.querySelectorAll('[role=menuitem]').length"` to confirm they exist in the DOM, then use `getByRole()` in Playwright code
9. Interact with the page to reach deeper states (click a button, open a dialog) then re-snapshot to capture the new state
10. Repeat for each page/component in the test plan
11. `playwright-cli close` — close the browser when done

## Workflow: Healer

1. `playwright-cli open` — launch browser
2. Log in using the auth helper above
3. `playwright-cli goto <page-where-test-failed>` — navigate to the failing page
4. `playwright-cli snapshot` — capture the ARIA tree
5. Find the element that the failing locator was targeting — check if it exists, has changed role/name, or is duplicated
6. Derive the corrected locator from the snapshot
7. `playwright-cli close` — close the browser when done

## Tips

- Use `playwright-cli snapshot --depth=3` for a high-level page structure overview
- Use full `playwright-cli snapshot` when you need details about a specific section
- If a strict-mode violation occurs, the snapshot will show all matching elements — count them to understand the ambiguity
- The ARIA tree shows `role`, `name`, and nesting — these map directly to `getByRole('role', { name: 'name' })`
