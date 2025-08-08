# MOFF CLI

**M**arkdown **O**rganization and **F**ormat **F**ramework

A command-line tool for validating and maintaining clean, organized documentation. Designed to work seamlessly with Large Language Models (LLMs) in modern IDEs like Cursor, VSCode, and Zed.

[![Python Version](https://img.shields.io/badge/python-3.12%2B-blue)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

## 🎯 Purpose

MOFF helps maintain consistent documentation structure across projects by:
- Validating markdown files against configurable rules
- Enforcing location constraints for different document types
- Checking frontmatter schemas and required fields
- Ensuring headers follow specified patterns and order
- Providing visual feedback through tree visualization

Perfect for projects where documentation quality and consistency matter, especially when working with AI assistants that parse markdown documentation.

## ✨ Features

- **📁 Smart Root Detection**: Automatically finds documentation root via `project_*.md` files
- **🔍 Comprehensive Validation**: Check frontmatter, headers, and file locations
- **🌳 Tree Visualization**: See your documentation structure with error highlighting
- **⚙️ Configurable Rules**: Define custom prefixes, patterns, and validation rules
- **💾 Result Persistence**: Save validation results for CI/CD integration
- **🎨 Rich Terminal Output**: Beautiful, colored output using Rich library

## 📦 Installation

### Using pip

```bash
pip install moff-cli
```

### Using uv (recommended)

```bash
uv add moff-cli
```

## 🚀 Quick Start

1. **Check your documentation** (creates `settings.json` automatically if not present):
```bash
moff check
```

2. **Visualize documentation structure**:
```bash
moff tree
```

## 📖 Usage

### Commands Overview

```bash
moff --help                    # Show help information
moff --version                 # Show version

moff check                     # Run validation checks
moff check --save             # Run checks and save results to moff_results.txt
moff check --path ./docs      # Check specific directory

moff tree                      # Display documentation tree
moff tree --errors-only       # Show only files with errors
moff tree --no-check          # Skip validation (faster)
```

### Example: Setting Up a Project

1. **Create a project file** (`project_myapp.md`):
```markdown
---
project: myapp
---

# Overview

This is my application's main documentation.

## Requirements

- Python 3.12+
- Rich library
```

2. **Create feature documentation** (`features/feature_auth.md`):
```markdown
---
project: myapp
feature: authentication
linked_features: ["users", "sessions"]
---

# Overview

Authentication system for the application.

## Requirements

- Secure password hashing
- JWT token support
- Session management
```

3. **Validate your documentation** (this will create `settings.json` if it doesn't exist):
```bash
moff check
```

### Example Output

#### Check Command
```
Collecting documentation files...
Root directory: /Users/you/project/docs

✓ All checks passed!

No validation issues found.
```

Or with errors:
```
Validation Summary:
  Total issues: 2
  Errors: 2

Issues found:

features/feature_broken.md:
  error [feature] headers.missing: Missing required header level=2 text='Requirements' (line 10)

tech_database.md:
  error [tech] location.subdirs_only: File must be in a subdirectory, not in root
```

#### Tree Command
```
📁 docs (documentation root)
├── 📁 features
│   ├── ⚡ feature_auth.md ✓
│   └── ⚡ feature_users.md ✓
├── 📁 technical
│   └── 🔧 tech_database.md ✓
└── 📋 project_myapp.md ✓

Summary:
  Total markdown files: 4
  Files with errors: 0
  Files with warnings: 0

✓ All files passed validation!
```

## 🐍 Programmatic Usage

When installed via pip, `moff-cli` can also be used as a Python library. Import it as `moff_cli`:

### Basic Validation

```python
from pathlib import Path
from moff_cli import Settings, Collector, Checker

# Load settings and collect documentation
settings = Settings()
collector = Collector(settings, start_path=Path.cwd())
collected_data = collector.collect()

# Run validation
checker = Checker(settings)
diagnostics = checker.check(collected_data)

# Process results
if not diagnostics:
    print("✓ All documentation is valid!")
else:
    for diag in diagnostics:
        print(f"{diag.path}: {diag.message}")
```

### Custom Configuration

```python
from moff_cli import (
    Settings,
    PrefixConfig,
    LocationConstraint,
    HeaderRule,
    HeaderMatch
)

# Create custom settings
settings = Settings()

# Add a custom prefix for API documentation
settings.prefixes["api"] = PrefixConfig(
    filename_pattern="api_*.md",
    location=LocationConstraint.SUBDIRS_ONLY,
    frontmatter_required={
        "endpoint": "string",
        "method": "string",
        "version": "string"
    },
    headers_required=[
        HeaderRule(level=1, text="Endpoint"),
        HeaderRule(level=2, text="Request"),
        HeaderRule(level=2, text="Response"),
    ]
)

# Save custom settings
settings.save_to_file(Path("settings.json"))
```

### Tree Visualization

```python
from moff_cli import Settings, Collector, Checker, TreeVisualizer
from rich.console import Console

console = Console()
settings = Settings()

# Collect and check
collector = Collector(settings)
collected_data = collector.collect()
checker = Checker(settings)
diagnostics = checker.check(collected_data)

# Display tree with error highlighting
visualizer = TreeVisualizer(settings, console)
visualizer.show_tree(collected_data, diagnostics)
```

### CI/CD Integration

```python
from pathlib import Path
from moff_cli import Settings, Collector, Checker, Severity

def validate_docs(project_path: Path) -> bool:
    """Validate documentation for CI/CD pipeline."""
    settings = Settings()
    collector = Collector(settings, start_path=project_path)
    checker = Checker(settings)

    # Collect and check
    collected = collector.collect()
    if collected.get("error"):
        print(f"ERROR: {collected['error']}")
        return False

    diagnostics = checker.check(collected)

    # Filter to only errors (ignore warnings)
    errors = [d for d in diagnostics if d.severity == Severity.ERROR]

    if errors:
        print(f"Validation failed with {len(errors)} errors")
        for error in errors:
            print(f"  ✗ {error.path}: {error.message}")
        return False

    return True

# Use in CI/CD
if not validate_docs(Path(".")):
    exit(1)
```

### Available Classes and Functions

- `Settings`: Configuration management
- `Collector`: File discovery and parsing
- `Checker`: Validation engine
- `TreeVisualizer`: Tree visualization
- `Diagnostic`: Validation issue representation
- `Severity`: Error, Warning, Info levels
- `LocationConstraint`: ROOT_ONLY, SUBDIRS_ONLY, ANY
- `HeaderOrder`: STRICT, IN_ORDER, ANY
- `HeaderMatch`: EXACT, REGEX

## ⚙️ Configuration

MOFF uses `settings.json` for configuration. The default configuration supports three document prefixes:

### Default Prefixes

| Prefix | Pattern | Location | Purpose |
|--------|---------|----------|---------|
| `project` | `project_*.md` | Root only | Main project documentation |
| `feature` | `feature_*.md` | Any | Feature specifications |
| `tech` | `tech_*.md` | Subdirs only | Technical implementation details |

### Custom Configuration Example

```json
{
  "version": 1,
  "root": {
    "detect": {
      "method": "project_file",
      "pattern": "project_*.md"
    },
    "override_path": null,
    "ignore": [
      "**/.git/**",
      "**/.venv/**",
      "**/node_modules/**",
      "**/archive/**"
    ]
  },
  "prefixes": {
    "api": {
      "filename": {
        "pattern": "api_*.md"
      },
      "location": "subdirs_only",
      "frontmatter": {
        "required": {
          "project": "string",
          "endpoint": "string",
          "method": "string"
        },
        "optional": {
          "deprecated": "boolean"
        }
      },
      "headers": {
        "required": [
          {
            "level": 1,
            "text": "Endpoint",
            "match": "exact"
          },
          {
            "level": 2,
            "text": "Request",
            "match": "exact"
          },
          {
            "level": 2,
            "text": "Response",
            "match": "exact"
          }
        ],
        "optional": [],
        "order": "in-order"
      }
    }
  }
}
```

### Configuration Options

#### Root Detection
- `detect.method`: Currently supports `"project_file"`
- `detect.pattern`: Glob pattern for root detection (default: `"project_*.md"`)
- `override_path`: Bypass auto-detection with explicit path
- `ignore`: List of glob patterns to exclude

#### Location Constraints
- `"root_only"`: File must be in root directory
- `"subdirs_only"`: File must be in a subdirectory
- `"any"`: File can be anywhere

#### Frontmatter Types
- `"string"`: Text values
- `"number"`: Numeric values (int or float)
- `"boolean"`: True/false values
- `"list"`: Array values
- `"object"`: Dictionary/object values

#### Header Order
- `"strict"`: Headers must appear in exact order
- `"in-order"`: Headers must be in order but others can appear between
- `"any"`: No order enforcement

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Uses [markdown-to-data](https://github.com/yourusername/markdown-to-data) for parsing
- Inspired by the need for better documentation tooling in AI-assisted development
