# Browser Investigation with dom-inspect

## Purpose

Before writing or fixing locators, inspect the **live DOM** using `dom-inspect`.
Unlike ARIA-only tools, `dom-inspect snapshot` surfaces `id`, `data-qa-selector`,
`data-testid`, and other DOM attributes directly — the exact values you need for
CSS-selector and data-attribute locators. Always verify against the real page.

## Quick Reference

| Command | Description |
|---------|-------------|
| `dom-inspect open [--state <f>] [--config <f>]` | Launch a browser; optionally restore auth state |
| `dom-inspect connect <wsEndpoint>` | Attach to an external browser via CDP |
| `dom-inspect goto <url>` | Navigate to a URL (waits for networkidle) |
| `dom-inspect snapshot [--config <f>]` | Capture full DOM attribute tree |
| `dom-inspect aria` | Capture ARIA accessibility tree |
| `dom-inspect locate <selector>` | Count matches + show tag/text/visible/enabled per match |
| `dom-inspect click <selector>` | Click an element |
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
dom-inspect click 'input[type="submit"], button[type="submit"]'
```

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
9. Click buttons/links to reach deeper states (dialogs, menus), then re-snapshot to capture new elements
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
