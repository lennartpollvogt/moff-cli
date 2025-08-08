---
project: moff-cli
feature: check
linked_features: [collector, save]
---

# Overview

The `check` feature validates the documentation set collected by the `collector` against the rules defined in `settings.json`. It ensures:
- files appear in allowed locations (root-only vs subdirectories),
- frontmatter (metadata) conforms to the configured schema,
- required headers are present with correct levels and in the correct order.

It prints results into the terminal and can save them into `moff_results.txt` in the documentation root (via the `save` feature).

## Inputs

- `settings.json` (effective settings, with defaults if the file is missing)
  - `root.detect` and `root.override_path` influence how the root was determined (already applied by the collector).
  - `prefixes` defines the set of valid prefixes, filename patterns, frontmatter schema, header rules, and location constraints.

- `collector` output (see `collector/feature_collector.md`)
  - `root_directory` (string)
  - `root` metadata:
    - `detection` (method, pattern, override_path_used)
    - `root_file` (path to the chosen project file)
    - `additional_root_candidates` (list of candidate project files)
  - one top-level object per prefix (e.g., `project`, `feature`, `tech`), where each file maps to:
    - `is_in_root` (boolean)
    - `md_list` (raw `markdown-to-data` output)

## Validation rules

- Root conditions
  - If `root.root_file` is missing and `override_path_used` is false, raise an error (no root identifiable).
  - If `additional_root_candidates` is non-empty, report a violation (multiple potential roots) — treated as an error by default.
  - If `project` group contains zero files, raise an error (missing project file at root).

- Location constraints
  - For each file under each prefix, evaluate `location` from settings:
    - `root_only` — `is_in_root` must be true.
    - `subdirs_only` — `is_in_root` must be false.
    - `any` — no constraint.
  - Any violation is reported as an error.

- Frontmatter (metadata)
  - For each file, find the first `md_list` item with the `metadata` key.
  - Validate presence and type of required keys for that file's prefix (types: string, number, boolean, list, object).
  - Optional keys, if present, must match their declared types.
  - Missing required metadata keys or type mismatches are errors.
  - If no `metadata` item exists and required metadata is configured, that is an error.

- Headers
  - Build the header sequence from `md_list` items that contain `header`.
  - For each prefix's `headers.required`:
    - Level must match exactly.
    - Text must match:
      - exact (default), or
      - regex if the rule specifies `"match": "regex"`.
  - `headers.order`:
    - `strict`: required headers must appear in the specified order with no reordering; other headers may exist between required ones.
    - `in-order`: required headers must appear in the specified order, but other headers may appear between them (default).
    - `any`: order is not enforced.
  - Missing headers or order violations are errors.

## Output and reporting

- Terminal output
  - Print each violation with:
    - file path (relative to `root_directory`)
    - prefix
    - rule category (root, location, frontmatter, headers)
    - a concise message
    - optional line hint (for headers, use the line of the matched/missing header when possible)
  - Provide a summary:
    - total files checked
    - total violations
    - exit code status

- Determinism
  - Files are processed in alphabetical order.
  - Violations are sorted by path, then by line number (if available), then by rule.

- Exit codes
  - Exit 0 when there are no violations.
  - Exit non-zero when there are violations (all are treated as errors by default).

- Severity
  - All violations are errors by default (non-zero exit).
  - Future versions may allow configuring severity per rule (`error`, `warning`, `info`), but this is not required for the first version.

## Internal result shape (example)

The `check` feature can internally represent its findings as a list of diagnostics, which can be printed and/or saved:

```json
[
  {
    "path": "moff-cli/moff-cli/tree/feature_tree.md",
    "prefix": "feature",
    "rule": "headers.missing",
    "message": "Missing required header level=2 text='Requirements'",
    "severity": "error",
    "line": null
  },
  {
    "path": "moff-cli/moff-cli/collector/tech_collector.md",
    "prefix": "tech",
    "rule": "location.subdirs_only",
    "message": "File is not allowed in root directory",
    "severity": "error",
    "line": null
  }
]
```

## Requirements

- consume the `collector` output and the effective `settings.json`
- validate:
  - root conditions (missing root, multiple candidates, missing project file)
  - per-file location constraints according to prefix `location`
  - frontmatter presence and types according to prefix `frontmatter`
  - header presence and order according to prefix `headers`
- print violations to the terminal with a summary
- return a non-zero exit code when violations exist
- support saving results via the `save` feature (`moff_results.txt` at the root directory)
