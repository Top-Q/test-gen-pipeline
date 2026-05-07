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
| `playwright-cli eval <js-expression>` | Evaluate JavaScript in the page |
| `playwright-cli close` | Close the browser |

Add `--raw` to any command to get unformatted output (useful for piping/parsing).

## Authentication Helper

Most pages require login. After opening the browser and navigating to the app:

```bash
playwright-cli goto http://localhost:8090/login
playwright-cli fill '#username' 'admin'
playwright-cli fill '#password' 'admin'
playwright-cli click 'input[type=submit]'
```

Wait for navigation to complete, then proceed to the target page.

## Workflow: POM Builder

1. `playwright-cli open` — launch browser
2. Log in using the auth helper above
3. `playwright-cli goto <module-page-url>` — navigate to the page you are building POs for
4. `playwright-cli snapshot` — capture the ARIA tree
5. Read the snapshot output — identify roles, names, and hierarchy
6. Derive locators from the snapshot (prefer `getByRole()` when names are unique, fall back to IDs/CSS)
7. Compare snapshot against what you derived from source code — fix discrepancies
8. Repeat for each page/component in the test plan
9. `playwright-cli close` — close the browser when done

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
