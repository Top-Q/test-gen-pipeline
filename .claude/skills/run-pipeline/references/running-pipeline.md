# Running the Pipeline

## Paths

- **Pipeline root**: `C:\Users\itaiag\git\node\test-gen-pipeline`
- **CLI entry**: `pipeline` (installed via `pip install -e .` from pipeline root)
- **Profiles dir**: `C:\Users\itaiag\git\node\test-gen-pipeline\profiles`
- **Artifacts dir**: `C:\Users\itaiag\git\node\test-gen-pipeline\artifacts`

## Pre-flight checks

Before running the pipeline:

```bash
# Verify the pipeline CLI is available
pipeline --help

# Check the profile exists and is valid
cat "C:\Users\itaiag\git\node\test-gen-pipeline\profiles\<profile>/profile.yaml"

# Verify the target project exists
ls "<project_root from profile.yaml>"

# Check that the target app is running (if needed for test execution)
curl -s -o /dev/null -w "%{http_code}" <base_url from profile.yaml>
```

## Running

```bash
# Full pipeline run
pipeline -v run --profile <name> --plan <path/to/plan.md> --ci

# Individual steps
pipeline -v build-pom --profile <name> --plan <path/to/plan.md> --ci
pipeline -v write-test --profile <name> --plan <path/to/plan.md> --ci
pipeline -v validate --profile <name> --files "<glob>"
pipeline -v heal --profile <name> --run-id <id> --ci

# Resume a failed run
pipeline -v run --profile <name> --plan <path/to/plan.md> --ci --resume <run-id>
```

**Always use `--ci`** when running from Claude Code (bypasses interactive permission prompts).
**Always use `-v`** for verbose logging.

The CLI writes logs to stderr and JSON result to stdout. Capture both:
```bash
pipeline -v run --profile openproject --plan plan.md --ci 2>pipeline.log
```

## Investigating results

After a run completes (success or failure):

1. **Find the latest run:**
   ```bash
   ls -t "C:\Users\itaiag\git\node\test-gen-pipeline\artifacts/" | head -1
   ```

2. **Read `run_state.json`** inside the artifact directory. Key sections to check:

   | Field | What to look for |
   |-------|-----------------|
   | `state` | Final state: `done` (success) or `failed` |
   | `generated_po_files` | List of PO/component files created |
   | `generated_test_files` | List of test spec files created |
   | `agent_invocations` | Each agent call — check `success`, `error`, `files_modified` |
   | `validation_results` | Lint, typecheck, structural — check `passed` and `output` |
   | `test_results` | Playwright execution — check `passed`, `error_output`, `failed_count` |
   | `failure_history` | Categorized failures — check `category`, `routed_to` |
   | `*_attempts` | How many times each agent was invoked |

3. **If tests failed**, read the `error_output` from the last `test_results` entry. Cross-reference with `failure_history` to see how it was classified and routed.

4. **If validation failed**, read the `output` from the failing `validation_results` entry. Common issues:
   - Lint errors → fix the generated files directly
   - TypeCheck errors → usually missing imports or wrong method signatures
   - Structural check violations → missing `.describe()`, `expect` in POs, missing `waitForLoad`

5. **If an agent failed**, read the `error` field in the `agent_invocations` entry. Check if it ran out of turns (max_turns limit) or hit an actual error.
