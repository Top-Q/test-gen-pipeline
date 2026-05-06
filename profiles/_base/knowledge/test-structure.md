# Generic Test Structure Patterns

## BDD Step Pattern
Tests use Given/When/Then steps wrapped in `test.step()` for structured logging.

## Test Isolation
Each test must be runnable independently. Never assume execution order.
If a test deletes an entity, it must first create that entity within the same test.

## Assertions
- Use Playwright's `expect()` with auto-waiting matchers
- Assertions belong in tests only — never in page objects
- Use locator getters from POs, then assert in test steps
