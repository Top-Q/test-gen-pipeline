# Browser Investigation with dom-inspect

## Purpose

Before writing or fixing locators, inspect the **live DOM** using `dom-inspect`.
Unlike ARIA-only tools, `dom-inspect snapshot` surfaces `id`, `data-qa-selector`,
`data-testid`, and other DOM attributes directly — the exact values you need for
CSS-selector and data-attribute locators. Always verify against the real page.

## Quick Reference

| Command | Description |
|---------|-------------|
| `dom-inspect open [--state <f>] [--config <f>] [--headless]` | Launch a browser; optionally restore auth state |
| `dom-inspect connect <wsEndpoint>` | Attach to an external browser via CDP |
| `dom-inspect goto <url>` | Navigate to a URL (waits for networkidle) |
| `dom-inspect snapshot [--config <f>] [--selector <css>]` | Capture DOM attribute tree; `--selector` scopes to a subtree |
| `dom-inspect aria [--selector <css>]` | Capture ARIA accessibility tree; `--selector` scopes to a subtree |
| `dom-inspect locate <selector>` | Count matches + show tag/text/visible/enabled per match |
| `dom-inspect click <selector> [--force]` | Click an element; `--force` bypasses visibility checks |
| `dom-inspect press <selector> <key>` | Focus element and press a key (e.g., `Enter`, `Tab`, `Escape`) |
| `dom-inspect fill <selector> <value>` | Fill an input field |
| `dom-inspect save-state <file>` | Save auth/session state to a JSON file |
| `dom-inspect clear-context` | Clear cookies, localStorage, sessionStorage |
| `dom-inspect close` | Close the browser and remove the session file |

## Session Persistence

`dom-inspect` stores a session at `~/.dom-inspect-session.json`. After `dom-inspect open`,
the browser runs as a background process — it survives the Bash tool call ending.
Each subsequent command reconnects to the same browser via the stored WebSocket endpoint.
**You do NOT need to reopen the browser between Bash calls** — the session persists.

## `snapshot` Output Format

The `snapshot` command walks the DOM and emits lines in this format:

```
{indent}{tag}[{attr}="{val}"]... "{own-text}" (visible|hidden)
```

Example:

```
div[id="main-menu"] (visible)
  nav[role="navigation"][aria-label="Main"] (visible)
    a[href="/work_packages"][data-qa-selector="nav-wp"] "Work Packages" (visible)
    a[href="/members"][data-qa-selector="nav-members"] "Members" (visible)
  button[id="add-member-btn"][data-qa-selector="add-member"][type="button"] "Add member" (visible)
  input[id="member-search"][type="text"][placeholder="Search members..."] (visible)
```

Only elements matching `focus_selectors` or having at least one `include_attribute` are shown.
Hidden elements are skipped by default.

### Scoped snapshot — use `--selector` after interactions

After clicking to open a dialog, dropdown, or menu, use `--selector` to snapshot only the new element. Full-page snapshots on complex pages produce thousands of lines and will be truncated:

```bash
# After opening a dialog or modal:
dom-inspect snapshot --selector '[role="dialog"]'
dom-inspect aria --selector '[role="dialog"]'

# After opening a dropdown menu or listbox:
dom-inspect snapshot --selector '[role="menu"]'
dom-inspect snapshot --selector '[role="listbox"]'

# After revealing a panel (use id or a stable class):
dom-inspect snapshot --selector '#my-panel-id'
```

Use `dom-inspect locate '[role="dialog"]'` or `dom-inspect locate '[role="menu"]'` first if you are not sure what selector identifies the newly-appeared element.

## `aria` Output Format

The `aria` command outputs the ARIA accessibility tree (same as `playwright-cli snapshot`):

```
- navigation "Main"
  - link "Work Packages"
  - link "Members"
- button "Add member"
- textbox "Search members..."
```

Use `aria` for accessible names needed by `getByRole()` locators.
Use `snapshot` first when you need `id`/`data-*` attribute values.

## `locate` Output Format

```
button[data-qa-selector="create-wp"]: 2 match(es)
  [0] tag=button, text="Create work package", visible=true, enabled=true
  [1] tag=button, text="Create work package", visible=false, enabled=true
```

Exit code **1** when 0 matches — use this to validate locators **before** writing them into PO files.

## Valid Selector Syntax for `locate`, `click`, `fill`, `press`

All selectors are passed to Playwright's `page.locator()`. Use **standard CSS** extended with Playwright pseudo-classes. Do **not** invent attribute syntax for text content.

### Attribute selectors (preferred — stable, unique)

```bash
dom-inspect locate '#my-id'                          # by id
dom-inspect locate '[data-qa-selector="create-wp"]'  # by data attribute
dom-inspect locate '[aria-label="Close dialog"]'     # by aria-label attribute
dom-inspect locate 'button[type="submit"]'           # tag + attribute
dom-inspect locate 'input[name="login"]'             # tag + name attribute
```

### Text content (Playwright pseudo-classes)

```bash
dom-inspect locate 'button:has-text("Save")'         # button containing "Save" (partial, case-insensitive)
dom-inspect locate 'li:has-text("Task")'             # list item containing "Task"
dom-inspect locate '[role="menuitem"]:has-text("Task")'  # role attribute + text
dom-inspect locate ':text("Save")'                   # any element whose trimmed text equals "Save"
```

### Role + text (combine attribute + pseudo-class)

```bash
dom-inspect locate '[role="option"]:has-text("Bug")'
dom-inspect locate '[role="menuitem"]:has-text("Task")'
dom-inspect locate 'a[role="menuitem"]:has-text("Task")'
```

### WRONG — do not use these

```bash
# WRONG: 'text' is not an HTML attribute — use :has-text() instead
dom-inspect locate 'menuitem[text="Task"]'           # ✗ invalid
dom-inspect locate '[text="Task"]'                   # ✗ invalid

# WRONG: 'menuitem' is a role value, not an HTML tag
dom-inspect locate 'menuitem'                        # ✗ no such HTML element

# WRONG: :text() as a suffix on a combined selector is not valid Playwright syntax
dom-inspect locate 'a[role="menuitem"]:text("Task")' # ✗ use :has-text() instead
```

### Visibility filter

```bash
dom-inspect locate 'button:has-text("Save"):visible'  # only visible matches
```

### XPath (when CSS is insufficient)

```bash
dom-inspect locate 'xpath=//button[@data-qa-selector="create-wp"]'
```

## Config Injection

The profile provides a `dom_inspector` configuration that filters noise for this specific app.
Write it to `/tmp/di-config.json` before opening the browser:

```bash
cat > /tmp/di-config.json << 'DICONFIG'
<DOM_INSPECTOR_CONFIG_JSON>
DICONFIG
dom-inspect open --config /tmp/di-config.json
```

See the "Profile dom_inspector config" section in this prompt for the JSON to use.
Pass `--config /tmp/di-config.json` to `snapshot` as well for per-command overrides.

## Authentication Helper

Most pages require login. Credentials come from the profile (see "Profile credentials" section).

```bash
dom-inspect open
dom-inspect goto <BASE_URL>/login
dom-inspect fill '#username' '<AUTH_USERNAME>'
dom-inspect fill '#password' '<AUTH_PASSWORD>'
dom-inspect press '#password' Enter
```

**Important:** Use `dom-inspect press '#password' Enter` to submit the login form — it is more reliable than clicking the submit button. The login submit element is `<input type="submit">`, not a `<button>`, so selectors like `button[type="submit"]` or `button:has-text("Sign in")` will match the wrong element (the navigation bar link).

Wait for navigation, then save the session so you don't need to log in again:

```bash
dom-inspect save-state /tmp/dom-inspect-auth.json
dom-inspect close
```

To reuse on subsequent runs:

```bash
dom-inspect open --state /tmp/dom-inspect-auth.json
dom-inspect goto <BASE_URL>
```

## Workflow: POM Builder

The browser is the **only** source of truth for locators. Do not derive locators from
source code — source code tells you where to navigate; the DOM snapshot tells you what to click.

1. Write `/tmp/di-config.json` from the profile's `dom_inspector` config (see "Config Injection")
2. `dom-inspect open --config /tmp/di-config.json` — launch browser with profile config
3. Log in using the auth helper above
4. `dom-inspect goto <module-page-url>` — navigate to the page you are building POs for
5. `dom-inspect snapshot` — find `id`, `data-qa-selector`, and other data attributes
6. `dom-inspect aria` — find accessible names for elements without stable data attributes
7. Choose locator strategy:
   - `id` or `data-qa-selector` present → `locator('#id')` or `locator('[data-qa-selector="..."]')`
   - No stable attribute → `getByRole('button', { name: '...' })` from the ARIA snapshot
8. **Validate before committing**: `dom-inspect locate '[data-qa-selector="your-selector"]'` — must exit 0 with 1 match
9. Click buttons/links to reach deeper states (dialogs, menus), then use `dom-inspect snapshot --selector '[role="dialog"]'` (or the appropriate selector) to capture only the new element — do NOT re-snapshot the full page
10. Repeat steps 4–9 for each page/component in the test plan
11. `dom-inspect close` — close the browser when done

## Workflow: Healer

1. `dom-inspect open` — launch browser (or reuse existing session)
2. Log in using the auth helper
3. `dom-inspect goto <page-where-test-failed>` — navigate to the failing page
4. `dom-inspect snapshot` — check if the element exists and what its current attributes are
5. `dom-inspect aria` — check accessible names if the locator uses `getByRole()`
6. `dom-inspect locate <failing-selector>` — confirms 0 matches; then find the working selector
7. Apply the corrected locator; `dom-inspect close` when done

## Tips

- `dom-inspect snapshot` first — it shows `id` and `data-*` directly; no eval needed
- `dom-inspect aria` for accessible names and Angular overlay elements (portals not in DOM tree)
- `dom-inspect locate` exit code 1 = 0 matches → locator is broken; use as pre-commit check
- The session persists across Bash calls — no need to reopen the browser each time
- For Angular overlays/CDK portals: use `dom-inspect aria` — they appear even when CSS-hidden
- **After clicking to open a dialog/menu, use `--selector` to scope the snapshot** — full-page snapshots on complex apps are large and will be truncated by the shell; `dom-inspect snapshot --selector '[role="dialog"]'` captures only what changed
- If `snapshot --selector` returns `[snapshot: no element matched selector "..."]`, run `dom-inspect locate '[role="dialog"]'` to find the correct selector for the newly-appeared element
