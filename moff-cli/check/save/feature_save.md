---
project: moff-cli
feature: save
linked_features: [check]
---

# Overview

This feature allows saving the results of a `check` run into the `moff_results.txt` file, placed in the documentation root (the directory determined by the `project_*.md` file or `override_path`).

## Output format

The saved file contains:
- Header with timestamp and summary statistics
- List of violations in deterministic order (by path, then by line, then by rule)
- Each violation includes: severity, file path (relative to root), optional line number, rule category, and message

Example `moff_results.txt`:
```
moff-cli check results
Generated: 2024-01-15 14:30:22 UTC
Root: moff-cli/moff-cli

Summary:
- Files checked: 5
- Violations: 2
- Status: FAILED

Violations:
[ERROR] collector/tech_collector.md | location.subdirs_only | File is not allowed in root directory
[ERROR] tree/feature_tree.md:15 | headers.missing | Missing required header level=2 text='Requirements'
```

## Integration with check

- The `check` feature can trigger saving via a CLI flag (e.g., `moff check --save` or `moff check -s`).
- Saving occurs after all validation is complete and does not affect the exit code logic.
- The save operation uses the same diagnostic data that is printed to the terminal.

## Requirements

- destination: `${root_directory}/moff_results.txt`
- contents:
  - header with timestamp and summary (files checked, violations, status)
  - list of violations in deterministic order (by path, line, rule)
  - each violation includes: severity, path (relative to root), optional line number, rule category, and message
- encoding: UTF-8
- write mode: overwrite the file (replace previous results)
- integration:
  - triggered by the `check` feature via CLI flag
  - saving never alters the exit code logic of `check` (violations still cause a non-zero exit)
