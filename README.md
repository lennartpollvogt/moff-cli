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

### From source

```bash
git clone https://github.com/yourusername/moff-cli.git
cd moff-cli
pip install -e .
```

## 🚀 Quick Start

1. **Initialize configuration** (creates `settings.json`):
```bash
moff init
```

2. **Check your documentation**:
```bash
moff check
```

3. **Visualize documentation structure**:
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

moff init                      # Create default settings.json
moff init --force            # Overwrite existing settings.json
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

2. **Initialize MOFF**:
```bash
moff init
```

3. **Create feature documentation** (`features/feature_auth.md`):
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

4. **Validate your documentation**:
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

## 🔧 Development

### Setting Up Development Environment

```bash
# Clone the repository
git clone https://github.com/yourusername/moff-cli.git
cd moff-cli

# Install with development dependencies
uv add --dev pytest black ruff

# Run tests
uv run pytest tests/ -v

# Run the CLI in development
uv run python -m moff_cli --help
```

### Running Tests

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=moff_cli

# Run specific test module
pytest tests/test_moff_cli.py::TestSettings
```

### Project Structure

```
moff-cli/
├── src/
│   └── moff_cli/
│       ├── __init__.py
│       ├── __main__.py
│       ├── __version__.py
│       ├── cli.py              # CLI interface
│       ├── settings/            # Configuration management
│       ├── collector/           # File discovery and parsing
│       ├── check/              # Validation engine
│       └── tree/               # Tree visualization
├── tests/
│   └── test_moff_cli.py       # Test suite
├── moff-cli/                   # Documentation specs
│   └── project_moff-cli.md    # Project documentation
├── pyproject.toml
└── README.md
```

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

1. Fork the repository
2. Create your feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines

- Follow PEP 8 style guide
- Add tests for new features
- Update documentation as needed
- Ensure all tests pass before submitting PR

## 📝 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Built with [Rich](https://github.com/Textualize/rich) for beautiful terminal output
- Uses [markdown-to-data](https://github.com/yourusername/markdown-to-data) for parsing
- Inspired by the need for better documentation tooling in AI-assisted development

## 🐛 Known Issues

- Some tech documentation files may need header level adjustments to comply with default rules
- Large documentation sets (>1000 files) may take a few seconds to process

## 📮 Support

- GitHub Issues: [github.com/yourusername/moff-cli/issues](https://github.com/yourusername/moff-cli/issues)
- Email: lennartpollvogt@protonmail.com

---

Made with ❤️ for better documentation