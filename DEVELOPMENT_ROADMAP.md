# MOFF-CLI Development Roadmap

## Project Overview
`moff-cli` is a command-line tool that helps maintain clean and organized documentation by validating markdown files against configurable rules. It's designed to work seamlessly with LLMs in IDEs like Cursor, VSCode, or Zed.

## Development Status

### ✅ Phase 1: Foundation (Completed)
- [x] **Settings Module** (`src/moff_cli/settings/`)
  - [x] Settings class with configuration management
  - [x] Default settings for project, feature, and tech prefixes
  - [x] JSON serialization/deserialization
  - [x] Type validation for frontmatter
  - [x] Support for location constraints, header rules, and patterns

- [x] **Collector Module** (`src/moff_cli/collector/`)
  - [x] Root directory detection via `project_*.md` files
  - [x] Override path support
  - [x] Recursive markdown file collection
  - [x] Ignore pattern support (`.git`, `.venv`, `node_modules`, etc.)
  - [x] File grouping by prefix patterns
  - [x] Integration with `markdown-to-data` library
  - [x] Location annotation (root vs subdirectory)

### ✅ Phase 2: Core Functionality (Completed)
- [x] **Check Module** (`src/moff_cli/check/`)
  - [x] Validation engine for collected files
  - [x] Location constraint validation
  - [x] Frontmatter schema validation
  - [x] Header presence and order validation
  - [x] Diagnostic message generation
  - [x] Exit code management
  - [x] **Save Sub-feature**
    - [x] Write results to `moff_results.txt`
    - [x] Include timestamp and statistics
    - [x] Detailed violation reporting

### ✅ Phase 3: Visualization & CLI (Completed)
- [x] **Tree Module** (`src/moff_cli/tree/`)
  - [x] Tree structure visualization
  - [x] Show only directories and markdown files
  - [x] Highlight inconsistencies from check results
  - [x] Integration with Rich library for terminal output
  - [x] Icon indicators for file types and status

- [x] **CLI Interface** (`src/moff_cli/cli.py`)
  - [x] Main entry point with argparse
  - [x] Commands:
    - [x] `moff check` - Run validation
    - [x] `moff check --save` - Run validation and save results
    - [x] `moff tree` - Display documentation structure
    - [x] `moff tree --errors-only` - Show only files with errors
    - [x] `moff tree --no-check` - Skip validation for faster display
    - [x] `moff init` - Create default settings.json
    - [x] `moff init --force` - Overwrite existing settings.json
  - [x] Help documentation
  - [x] Version information (`--version`)
  - [x] Module execution support (`python -m moff_cli`)

### ✅ Phase 4: Package Configuration (Completed)
- [x] **Package Setup**
  - [x] Update `pyproject.toml` with entry points
  - [x] Configure console scripts
  - [x] Add package metadata
  - [x] Configure build system
  - [x] Add development dependencies

### ✅ Phase 5: Testing (Completed - Basic)
- [x] **Unit Tests** (`tests/`)
  - [x] Settings module tests (3 test cases)
  - [x] Collector module tests (3 test cases)
  - [x] Check module tests (3 test cases)
  - [x] Integration test (full workflow)
  - [x] All tests passing (10/10)

### 📋 Phase 6: Documentation (In Progress)
- [ ] **User Documentation**
  - [ ] Update README.md with usage examples
  - [ ] Installation instructions
  - [ ] Configuration guide
  - [ ] Troubleshooting section

- [ ] **Developer Documentation**
  - [ ] API documentation
  - [ ] Contributing guidelines
  - [ ] Architecture overview

## Current Implementation Details

### Completed Features
1. **Settings Management**
   - Full JSON schema support
   - Default configurations for project, feature, and tech prefixes
   - Custom prefix support
   - Type validation for frontmatter fields

2. **File Collection**
   - Automatic root detection via `project_*.md`
   - Override path support for custom roots
   - Recursive directory traversal
   - Glob pattern matching for ignore rules
   - Markdown file parsing with `markdown-to-data`

3. **Validation Engine**
   - Location constraint checking (root_only, subdirs_only, any)
   - Frontmatter validation (required/optional fields with type checking)
   - Header validation (presence, level, text matching, order)
   - Comprehensive diagnostic reporting
   - Exit code management for CI/CD integration

4. **Tree Visualization**
   - Rich terminal output with colors and icons
   - Error/warning highlighting
   - Filtering options (errors-only mode)
   - Summary statistics

5. **CLI Commands**
   - Full command-line interface with subcommands
   - Help text and usage examples
   - Verbose mode for debugging
   - Settings file initialization

### Known Issues Found During Development
1. **Documentation Issue**: `moff-cli/settings/tech_settings.md` has "Implementation Details" as a level 2 header instead of level 1 (as required by default settings)
   - Status: Correctly detected by the checker
   - Action: Documentation needs to be fixed to comply with rules

## Next Steps

### Priority 1: Documentation
- [ ] Write comprehensive README.md
- [ ] Create installation guide
- [ ] Document all CLI commands with examples
- [ ] Add configuration examples for different use cases

### Priority 2: Polish & Enhancement
- [ ] Add color configuration options
- [ ] Add quiet/verbose modes globally
- [ ] Improve error messages with suggestions
- [ ] Add `--format` option for different output formats (JSON, YAML)

### Priority 3: Advanced Features (Future)
- [ ] Watch mode for continuous checking
- [ ] Auto-fix capabilities for simple issues
- [ ] Custom rule plugins
- [ ] Integration with git hooks
- [ ] GitHub Actions workflow template

## Dependencies Status
- ✅ `markdown-to-data>=2.0.0` - Installed and working
- ✅ `rich>=14.1.0` - Installed and working
- ✅ `pytest>=8.4.1` - Installed for testing

## Technical Decisions Made
1. Using dataclasses for configuration objects
2. Enum types for constraint values
3. Pathlib for all file operations
4. Rich library for terminal output formatting
5. JSON for settings storage (as specified)
6. Argparse for CLI (built-in, no extra dependencies)
7. Class-based architecture for modularity

## Success Metrics Achieved
- ✅ All commands work as specified in documentation
- ✅ Exit codes correctly indicate success/failure
- ✅ Settings.json is created on first run without overwriting
- ✅ All test cases pass (10/10)
- ✅ Tree visualization with error highlighting
- ✅ Comprehensive diagnostic reporting
- ✅ Save results to file functionality

## Performance Characteristics
- Fast collection and validation (<1s for typical projects)
- Memory efficient (streaming file processing)
- Deterministic output (sorted file lists)
- Graceful error handling (permission errors, missing files)

## Timeline Summary
- Phase 1-5: Completed in single development session
- Estimated remaining work: 1-2 hours for documentation

---
*Last Updated: Development session completed core functionality*
*Status: Core implementation complete, documentation pending*