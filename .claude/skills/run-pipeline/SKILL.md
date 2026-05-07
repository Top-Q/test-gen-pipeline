---
name: run-pipeline
description: Run the test generation pipeline. Configures profiles, executes the CLI, investigates results, and updates knowledge files. Use when the user wants to generate tests, run the pipeline, investigate a run, or update pipeline knowledge.
allowed-tools: Bash(run-pipeline:*), Read, Edit, Write, Glob, Grep
---

# Run Pipeline Skill

Operate the test generation pipeline as an interactive interface. The architecture and schemas are documented in CLAUDE.md — this skill covers the operational workflow.

## Workflow

### 1. Determine what the user wants

- **Run the full pipeline** — generate POs + tests + execute + heal
- **Run a single step** — just build POMs, just write tests, just validate, or just heal
- **Investigate a past run** — look at artifacts and diagnose issues
- **Update knowledge** — improve knowledge files based on run results
- **Configure a profile** — create or modify a profile for a project
- **Create a test plan** — author a new test plan markdown file

### 2. Pre-flight, run, and investigate

See: [references/running-pipeline.md](references/running-pipeline.md)

### 3. Update knowledge or create test plans

See: [references/knowledge-and-plans.md](references/knowledge-and-plans.md)

### 4. Troubleshooting

See: [references/troubleshooting.md](references/troubleshooting.md)
