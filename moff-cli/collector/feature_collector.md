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

The returned data is a dictionary in the following format:

```python
{
    "root_directory": "moff-cli/moff-cli",
    "root": {
        "project": {
            "moff-cli/moff-cli/project_moff-cli.md": [
                {'metadata': {'project': 'moff-cli'}, 'start_line': 1, 'end_line': 3},
                {'header': {'level': 1, 'content': 'Overview: moff_project'}, 'start_line': 5, 'end_line': 5},
                ... # rest of content parsed with `markdown-to-data` library
            ]
        }
    },
    "feature": {
        "moff-cli/collector/feature_collector.md": [content],
        "moff-cli/check/feature_check.md": [content],
        "moff-cli/tree/feature_tree.md": [content]
    },
    "tech": {
        "moff-cli/collector/tech_collector.md": [content]
    }
}
```

The objects `project`, `feature` and `tech` is based the allowed specified prefixes for files. Each object containts the file path and content of the corresponding file with the prefix.

## Requirements

- collect, based on the `settings.json` file the file with the specified prefixes
- ignores all files which do not have a specified prefix within the `settings.json` file
-
