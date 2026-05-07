# Troubleshooting

## Common issues

### Pipeline CLI not found

```
Error: No such command 'run'.
```

Install the pipeline package in development mode:
```bash
cd "C:\Users\itaiag\git\node\test-gen-pipeline"
pip install -e .
```

### Profile not found

```
FileNotFoundError: Profile not found: .../profiles/<name>/profile.yaml
```

- Check that the profile directory and YAML file exist
- If using `--profiles-dir`, verify the path is correct

### Barrel export or fixture file not found

```
FileNotFoundError: Barrel export file not found: ...
FileNotFoundError: Fixture file not found: ...
```

The profile references files in the target project that don't exist yet. Create them or update the profile YAML.

### Agent fails repeatedly (max attempts)

Check the `agent_invocations` in `run_state.json`:
- `error` field shows what went wrong
- If the agent ran out of turns, the task may be too large — split the test plan into smaller component groups
- If the error is about missing files, check that the target project's structure matches the profile config

### Agent produces invalid code

Check `validation_results` in `run_state.json`:
- **Lint failures**: Usually fixable formatting or style issues. Fix the files and re-run `pipeline validate`
- **TypeCheck failures**: Often wrong import paths or calling methods that don't exist on PO contracts. Check if knowledge files need updating
- **Structural failures**: Missing `.describe()` on locators, `expect` imported in POs, or missing `waitForLoad()`. Fix and validate

### Tests fail at runtime

Check `test_results` and `failure_history` in `run_state.json`:

| Failure category | Likely cause | Action |
|-----------------|-------------|--------|
| `timeout` | Locator doesn't match any element, or app is slow | Update `dom-quirks.md` or `locator-patterns.md` |
| `locator_not_found` | Multiple elements match (strict mode) | Scope locator to container, use IDs |
| `assertion_mismatch` | Expected value doesn't match actual | Check if test plan expectations are correct |
| `missing_method` | Test calls a PO method that doesn't exist | Re-run POM Builder or update PO contracts |
| `import_error` | Module path is wrong or export is missing | Check `barrel_export` in profile, verify `internals.ts` |
| `infrastructure` | App is not running or network issue | Start the target app, check `base_url` |

### Repeated failure causes immediate abort

The classifier detects identical failures (same category + message). If the healer can't fix it:
1. Read the error output manually
2. Fix the root cause in the PO or test file
3. Re-run with `--resume`

### Windows: WinError 206 (command line too long)

The `AgentRunner` handles this automatically by writing long system prompts to temp files. If you still see this error, the issue is elsewhere — check the Bash command length.

### playwright-cli not found

Agents need `playwright-cli` for live DOM inspection:
```bash
npm install -g @playwright/cli
```

Without it, agents will still work but can't inspect the live DOM to verify locators.

## Debugging a run

### Step-by-step investigation

1. Find the run: `ls -t artifacts/ | head -5`
2. Read state: `cat artifacts/<run-id>/run_state.json`
3. Check final state: is it `done` or `failed`?
4. If `failed`, check `failure_history[-1]` for the last failure category
5. Check `agent_invocations` — find the last one with `success: false`
6. Read its `error` field for the actual error message
7. Check `validation_results` for any failed checks
8. Read the generated files listed in `generated_po_files` and `generated_test_files`

### Resuming after manual fixes

After fixing files manually:
```bash
pipeline -v run --profile <name> --plan <plan> --ci --resume <run-id>
```

This reloads the state from `run_state.json` and continues from the last saved state.
