# Common Playwright Failure Patterns

## Timeout Errors
- `waiting for locator` — element not found within timeout
- Check if the element exists in the DOM (wrong locator vs not loaded yet)
- Common causes: wrong selector, element behind overlay, slow page load

## Strict Mode Violations
- `strict mode violation` / `resolved to N elements`
- Multiple elements match the locator — need to scope or be more specific
- Fix: scope to a container, use `exact: true`, or filter with `.nth()`

## Assertion Mismatches
- `expect(received)` failures
- Actual value doesn't match expected
- Check for race conditions — use auto-waiting matchers

## Import/Module Errors
- `Cannot find module` — missing export in barrel file or wrong path
- `no exported member` — class not exported from the module
- Fix: add to internals.ts, check relative paths

## Infrastructure Errors
- `ECONNREFUSED` — application server not running
- `net::ERR` — network connectivity issues
- These are NOT code issues — check environment
