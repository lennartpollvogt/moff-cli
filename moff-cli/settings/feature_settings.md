---
project: moff-cli
feature: settings
linked_features: [check]
---

# Overview

The `settings` feature defines how `moff-cli` discovers the documentation root, which Markdown files are considered (by prefix), what structure each file type must follow (frontmatter and headers), and where those files are allowed to live (root vs subdirectories). It is designed to be:
- opinionated by default (works without any settings file),
- declarative and minimal when customized,
- easy to validate and reason about for both humans and LLMs.

The configuration file is named `settings.json` and must be located at the documentation root (the directory determined by the `project_*.md` file unless overridden). If no `settings.json` is present, built-in defaults are used. The CLI creates a default `settings.json` on first run if it does not already exist.

## Schema

The settings file follows this schema. Fields marked “(default)” are optional and will be filled by built-in defaults when omitted.

```/dev/null/settings.schema.json#L1-200
{
  "version": 1,
  "root": {
    "detect": {
      "method": "project_file",                // currently only "project_file" is supported
      "pattern": "project_*.md"                // glob used to find the root-defining file
    },
    "override_path": null,                     // string | null — when set, bypasses auto-detection
    "ignore": [                                // list of glob patterns to exclude during collection
      "**/.git/**",
      "**/.venv/**",
      "**/node_modules/**"
    ]
  },
  "prefixes": {
    "<prefix_name>": {
      "filename": {
        "pattern": "prefix_*.md"               // (default) inferred as "<prefix_name>_*.md" if omitted
      },
      "location": "any",                        // one of: "any" (default) | "root_only" | "subdirs_only"
      "frontmatter": {
        "required": {                           // key: type — types: "string" | "number" | "boolean" | "list" | "object"
          // e.g., "project": "string"
        },
        "optional": {
          // e.g., "linked_features": "list"
        }
      },
      "headers": {
        "required": [                           // ordered list of required headers
          {
            "level": 1,                         // Markdown heading level (integer)
            "text": "Overview",                 // prefer exact header matches by default
            "match": "exact"                    // one of: "exact" | "regex" (default: "exact" if omitted)
          }
        ],
        "optional": [                           // headers that are helpful but not mandatory
          // same shape as required items
        ],
        "order": "in-order"                     // one of: "strict" | "in-order" | "any" (default: "in-order")
      }
    }
  }
}
```

Notes:
- `location` consolidates “allowed in root” and “allowed in subfolders” into one field:
  - `root_only` — must be placed in the root directory,
  - `subdirs_only` — must not be in the root directory,
  - `any` — can appear in both.
- `headers.order`:
  - `strict`: required headers must appear in exactly the given order with no other required headers in between,
  - `in-order`: required headers must appear in the given order but other headers may appear between them,
  - `any`: order is not enforced.

## Defaults

`moff-cli` ships with opinionated defaults that require no `settings.json`. These defaults match the intended structure of this project with the prefixes `project`, `feature`, and `tech`.

```/dev/null/.default_settings.json#L1-200
{
  "version": 1,
  "root": {
    "detect": { "method": "project_file", "pattern": "project_*.md" },
    "override_path": null,
    "ignore": ["**/.git/**", "**/.venv/**", "**/node_modules/**"]
  },
  "prefixes": {
    "project": {
      "filename": { "pattern": "project_*.md" },
      "location": "root_only",
      "frontmatter": {
        "required": { "project": "string" },
        "optional": {}
      },
      "headers": {
        "required": [
          { "level": 1, "text": "Overview", "match": "exact" }
        ],
        "optional": [
          { "level": 2, "text": "Requirements", "match": "exact" }
        ],
        "order": "in-order"
      }
    },
    "feature": {
      "filename": { "pattern": "feature_*.md" },
      "location": "any",
      "frontmatter": {
        "required": { "project": "string", "feature": "string" },
        "optional": { "linked_features": "list" }
      },
      "headers": {
        "required": [
          { "level": 1, "text": "Overview", "match": "exact" },
          { "level": 2, "text": "Requirements", "match": "exact" }
        ],
        "optional": [],
        "order": "strict"
      }
    },
    "tech": {
      "filename": { "pattern": "tech_*.md" },
      "location": "subdirs_only",
      "frontmatter": {
        "required": { "project": "string" },
        "optional": { "feature": "string", "linked_features": "list" }
      },
      "headers": {
        "required": [
          { "level": 1, "text": "Technical Details", "match": "exact" },
          { "level": 1, "text": "Implementation Details", "match": "exact" }
        ],
        "optional": [],
        "order": "in-order"
      }
    }
  }
}
```

## Examples

Minimal `settings.json` using only defaults (you can omit this file entirely):
```/dev/null/settings.minimal.json#L1-40
{
  "version": 1
}
```

Customizing locations and ignores:
```/dev/null/settings.example.json#L1-120
{
  "version": 1,
  "root": {
    "detect": { "method": "project_file", "pattern": "project_*.md" },
    "ignore": ["**/.git/**", "**/.venv/**", "**/archive/**"]
  },
  "prefixes": {
    "project": { "location": "root_only" },
    "feature": { "location": "any" },
    "tech": { "location": "subdirs_only" }
  }
}
```

Adding stricter header rules for `feature` pages:
```/dev/null/settings.headers.json#L1-200
{
  "version": 1,
  "prefixes": {
    "feature": {
      "headers": {
        "required": [
          { "level": 1, "text": "Overview", "match": "exact" },
          { "level": 2, "text": "Requirements", "match": "exact" },
          { "level": 2, "text": "Acceptance Criteria", "match": "exact" }
        ],
        "order": "in-order"
      }
    }
  }
}
```

## Validation and behavior

- Root detection
  - If `override_path` is provided and exists, it is used as the documentation root.
  - Otherwise, the first file matching `root.detect.pattern` (default `project_*.md`) determines the root directory.
  - If no project file is found and no override is provided, `moff` errors with a clear message.

- Collection
  - Only `.md` files are considered.
  - Files are matched against known `prefixes` by `filename.pattern` (default `<prefix>_*.md`).
  - Files that match no configured prefix are ignored.

- Location constraints
  - `root_only`: file must be directly in the root directory.
  - `subdirs_only`: file must not be directly in the root directory.
  - `any`: no constraint.

- Frontmatter validation
  - Each required key must be present and match the declared type.
  - Optional keys, if present, must match their declared type.

- Header validation
  - `required` headers must be present and conform to `level`, `text`, and `match`.
  - `order` is enforced per the configured strategy (`strict`, `in-order`, or `any`).

- Output
  - The `check` feature prints a summary of all violations with file paths and line hints.
  - Severity levels classify issues by impact:
    - error — fails the command (non-zero exit code) and should be fixed
    - warning — reported but does not fail the command
    - info — advisory notes that do not affect status
  - Default behavior: all violations are treated as errors. Future versions may allow configuring severity per rule or per prefix.

- Bootstrapping
  - If `settings.json` is missing, `moff` runs with defaults.
  - `moff` creates a default `settings.json` on first run (without overwriting an existing file).

## Requirements

- has to be named `settings.json`
- has to be placed in the root directory of the documentation (as determined by root detection, unless overridden)
- if missing, defaults are used and the file is created on first run (only when it is not already present)
- must support:
  - root detection via `project_*.md` (with optional `override_path`)
  - ignore patterns
  - prefix definitions for `project`, `feature`, and `tech`
  - per-prefix filename patterns, location constraints, frontmatter schema, and header rules
- should remain simple and declarative; no imperative rules or code execution
