---
project: moff-cli
feature: collector
linked_features: [feature_collector.md]
---

# Technical Details

The collector feature requires the following technologies:

- `markdown-to-data` library
- `pathlib` library for directory and file operations

# Implementation Details

## `markdown-to-data' Library

The `markdown-to-data` library is used to convert Markdown files into python list of dictionaries. It provides a simple and efficient way to extract information from Markdown files and store it in a structured format.

Link to [markdown-to-data README](https://github.com/lennartpollvogt/markdown-to-data/blob/main/README.md)

The purpose of this library within `moff-cli` is to collect the content of each markdown file and save it into a structured format, which represents the hierarchy of the project's repository.

**Usage**:
```python
from markdown_to_data import Markdown

markdown = """
---
title: Example text
author: John Doe
---

# Main Header

- [ ] Pending task
    - [x] Completed subtask
- [x] Completed task

## Table Example
| Column 1 | Column 2 |
|----------|----------|
| Cell 1   | Cell 2   |

´´´python
def hello():
    print("Hello World!")
´´´
"""

md = Markdown(markdown)

# Get parsed markdown as list
print(md.md_list)
```

**Output for `md.md_list`**:
```python
[
    {
        'metadata': {'title': 'Example text', 'author': 'John Doe'},
        'start_line': 2,
        'end_line': 5
    },
    {
        'header': {'level': 1, 'content': 'Main Header'},
        'start_line': 7,
        'end_line': 7
    },
    {
        'list': {
            'type': 'ul',
            'items': [
                {
                    'content': 'Pending task',
                    'items': [
                        {
                            'content': 'Completed subtask',
                            'items': [],
                            'task': 'checked'
                        }
                    ],
                    'task': 'unchecked'
                },
                {'content': 'Completed task', 'items': [], 'task': 'checked'}
            ]
        },
        'start_line': 9,
        'end_line': 11
    },
    {
        'header': {'level': 2, 'content': 'Table Example'},
        'start_line': 13,
        'end_line': 13
    },
    {
        'table': {'Column 1': ['Cell 1'], 'Column 2': ['Cell 2']},
        'start_line': 14,
        'end_line': 16
    },
    {
        'code': {
            'language': 'python',
            'content': 'def hello():\n    print("Hello World!")'
        },
        'start_line': 18,
        'end_line': 21
    }
]
```
