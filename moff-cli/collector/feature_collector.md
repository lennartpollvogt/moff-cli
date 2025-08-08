---
project: moff-cli
feature: collector
linked_features: [check, tree]
---

# Overview

The `collector` feature is the starting point of the `moff-cli` application. It checks the project structure and collects all markdown files.
First, it searches for `project_` (.md) file to find the root directory. Second, it searches for all markdown files within the root directory and its subdirectories. Third, extracts the content of each markdown file, processes it with the `markdown-to-data` library and returns the data.

Let's assume the root directory looks like this:

```
moff-cli/
├── moff-cli/
│   ├── project_moff-cli.md
│   ├── collector/
│   │   ├── feature_collector.md
│   │   ├── tech_collector.md
│   ├── tree/
│   │   ├── feature_tree.md
│   ├── check/
│   │   └── feature_check.md
│   └── ...
├── README.md
└── main.py
```

## Inputs from `settings.json`

- Root detection
  - Use `root.override_path` when provided; otherwise auto-detect using `root.detect.method` and `root.detect.pattern` (default: `project_*.md`).
  - Apply `root.ignore` globs during traversal (default ignores: `.git`, `.venv`, `node_modules`, etc.).
- Prefixes and filename patterns
  - The set of valid prefixes is taken from `settings.prefixes` keys (e.g., `project`, `feature`, `tech`).
  - For each prefix, match files by `filename.pattern`. If omitted, default to `<prefix>_*.md`.
- Location constraints
  - The collector does not enforce `location` rules (`root_only`, `subdirs_only`, `any`); it annotates files so the `check` feature can enforce them.

## Discovery algorithm

1) Determine the documentation root
- If `override_path` is provided and exists, use it as root.
- Otherwise, search for the first file that matches `root.detect.pattern` starting from the repository level, using a deterministic, alphabetical traversal. The directory containing this file is the root.
- When multiple root-defining files are found, select the first deterministically and record other candidates in metadata.
- If none is found and no `override_path` is set, stop with an error (the `check` feature can format messaging).

2) Traverse the tree from the root
- Recursively walk the root directory.
- Apply `root.ignore` patterns to skip directories/files.
- Consider only files with a `.md` extension.
- Normalize paths to be relative to the documentation root.

3) Match files to prefixes and parse
- For each `.md` file, check it against each prefix’s `filename.pattern`. If it matches none, ignore it.
- For matched files, parse the content using `markdown-to-data` and keep the resulting `md_list` as-is (no validation here).
- Annotate each file with:
  - `is_in_root`: whether the file is directly in the root directory.
  - `matched_prefix`: the prefix that matched (for internal use; grouping uses the prefix key).
- Ensure deterministic output by sorting file paths alphabetically within each prefix.

## Returned data shape

```json
{
  "root_directory": "moff-cli/moff-cli",
  "root": {
    "detection": {
      "method": "project_file",
      "pattern": "project_*.md",
      "override_path_used": false
    },
    "root_file": "moff-cli/moff-cli/project_moff-cli.md",
    "additional_root_candidates": []
  },
  "project": {
    "moff-cli/moff-cli/project_moff-cli.md": {
      "is_in_root": true,
      "md_list": [
        { "metadata": { "project": "moff-cli" }, "start_line": 1, "end_line": 3 },
        { "header": { "level": 1, "content": "Overview: moff_project" }, "start_line": 5, "end_line": 5 }
      ]
    }
  },
  "feature": {
    "moff-cli/moff-cli/collector/feature_collector.md": {
      "is_in_root": false,
      "md_list": [/* parsed content from markdown-to-data */]
    },
    "moff-cli/moff-cli/check/feature_check.md": {
      "is_in_root": false,
      "md_list": [/* parsed content from markdown-to-data */]
    },
    "moff-cli/moff-cli/tree/feature_tree.md": {
      "is_in_root": false,
      "md_list": [/* parsed content from markdown-to-data */]
    }
  },
  "tech": {
    "moff-cli/moff-cli/collector/tech_collector.md": {
      "is_in_root": false,
      "md_list": [/* parsed content from markdown-to-data */]
    }
  }
}
```

Notes:
- Grouping keys (`project`, `feature`, `tech`) are derived from `settings.prefixes` keys.
- `md_list` is the raw output from `markdown-to-data`. Header text is exposed as `header.content`. The `check` feature compares this against `headers[].text` from settings (exact matching by default).
- The collector does not enforce frontmatter types, header presence/order, or location constraints; it only collects and annotates.

## Requirements

- Root
  - Use `root.override_path` if set; otherwise detect root by `root.detect` (default `project_*.md`).
  - If multiple root candidates are found, select deterministically and record all candidates in metadata.
  - If no root can be determined and no override is provided, return an error.
- Traversal and selection
  - Apply `root.ignore` globs.
  - Only consider `.md` files.
  - Match files by prefix `filename.pattern` (default `<prefix>_*.md`); ignore files that match no configured prefix.
- Parsing and annotation
  - Parse matched files with `markdown-to-data` into `md_list`.
  - Annotate each file with `is_in_root`.
  - Sort file paths alphabetically within each prefix for deterministic output.
- Output
  - Return a dictionary with:
    - `root_directory` (string),
    - `root` metadata (detection details, chosen `root_file`, and `additional_root_candidates`),
    - one top-level object per prefix, each mapping file paths to `{ is_in_root, md_list }`.
