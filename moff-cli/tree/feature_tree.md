---
project: moff-cli
feature: tree
linked_features: [collector, check]
---

# Overview

The `tree` feature which is also a `moff` command (`moff tree`) prints the directory structure of the project into the cli.
It only shows folders and markdown files.

Example output:
```
moff-cli
├── project_moff-cli.md
├── check
│   ├── feature_check.md
│   └── tech_check.md
│   └── save
│       ├── feature_save.md
│       └── tech_save.md
├── collector
│   ├── feature_collector.md
│   └── tech_collector.md
```

## Requirements

- printing the directory structure
- the root folder is where the project's file (`project_`; e.g. `project_moff-cli.md`) is located.
- only considering files with a `.md` extension
- considering subfolders
- providing information about inconsistencies in the directory structure (coming from the `check` feature)
