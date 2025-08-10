---
project: moff-cli
feature: fix
linked_features: [check, settings]
---

# Technical Details

The fix feature provides automatic correction of certain validation issues detected by the check command. It integrates with the existing validation pipeline to apply safe, deterministic fixes to documentation files.

## Dependencies

- `pyyaml` - for parsing and generating YAML frontmatter
- `pathlib` (standard library) - for file path operations
- `typing` - for type hints
- `re` (standard library) - for pattern matching in diagnostic messages

# Implementation Details

## Architecture

The fix feature is implemented through a separate `Fixer` class that works alongside the `Checker` class. This separation of concerns allows for:
- Independent testing of fix logic
- Clear distinction between detection and correction
- Future extensibility for additional fix types

## Fixable Rules

The following diagnostic rules are automatically fixable:

```python
FIXABLE_RULES = {
    "frontmatter.missing",      # Add complete frontmatter block
    "frontmatter.missing_field", # Add missing fields to existing frontmatter
    "headers.missing",          # Add missing required headers
    "headers.wrong_level"       # Correct header levels (future)
}
```

Non-fixable issues include:
- `location.*` - File location constraints (requires moving files)
- `headers.order` - Header ordering issues (requires context-aware reordering)
- `frontmatter.type_mismatch` - Type errors in existing values (requires user input)

## Core Components

### Diagnostic Enhancement

The `Diagnostic` class tracks fixability:

```python
class Diagnostic:
    FIXABLE_RULES = {...}
    
    def __init__(self, ...):
        self.fixable = rule in self.FIXABLE_RULES
```

### Fixer Class

Located in `moff_cli/check/fixer.py`, the `Fixer` class handles all automatic fixes:

```python
class Fixer:
    def fix_files(collected_data, diagnostics) -> Dict[str, List[str]]:
        """Main entry point for fixing multiple files"""
        
    def fix_file(file_path, diagnostics, md_data, prefix_name) -> List[str]:
        """Fix issues in a single file"""
        
    def _fix_frontmatter_issues(...):
        """Handle frontmatter-related fixes"""
        
    def _fix_header_issues(...):
        """Handle header-related fixes"""
```

## Fix Strategies

### Frontmatter Fixes

1. **Missing Frontmatter**
   - Inserts complete YAML block at file start
   - Adds all required fields with appropriate empty values
   - Includes commonly used optional fields (e.g., `linked_features`)

2. **Missing Fields**
   - Parses existing YAML frontmatter
   - Adds missing required fields with type-appropriate defaults:
     - `string`: `""`
     - `number`: `0`
     - `boolean`: `false`
     - `list`: `[]`
     - `object`: `{}`

### Header Fixes

1. **Missing Headers**
   - Determines optimal insertion point based on:
     - Position relative to other required headers
     - Existing content structure
     - Frontmatter boundaries
   - Maintains proper spacing (blank lines before/after)

2. **Wrong Level** (detected but not currently auto-fixed)
   - Identifies headers with incorrect levels
   - Future: Could update header prefix while preserving text

## File Processing Pipeline

```python
def fix_files(collected_data, diagnostics):
    # 1. Group diagnostics by file
    diagnostics_by_file = group_by_file(diagnostics)
    
    # 2. Process each file
    for file_path, file_diagnostics in diagnostics_by_file:
        # 3. Resolve file path (handle temp directories)
        full_path = resolve_path(file_path, root_dir)
        
        # 4. Find prefix configuration
        prefix_name = find_prefix(file_path, collected_data)
        
        # 5. Apply fixes in order
        #    - Frontmatter first (affects line numbers)
        #    - Headers second
        lines = read_file(full_path)
        lines = fix_frontmatter(lines, ...)
        lines = fix_headers(lines, ...)
        
        # 6. Write back if changes made
        if fixes_applied:
            write_file(full_path, lines)
```

## CLI Integration

The fix feature is triggered via the `--fix` flag:

```python
# In cli.py
if args.fix:
    fixable = [d for d in diagnostics if d.fixable]
    if fixable:
        fixer = Fixer(settings)
        fixes_applied = fixer.fix_files(collected_data, diagnostics)
        
        # Show applied fixes
        for file_path, fixes in fixes_applied.items():
            print(f"Fixed {file_path}:")
            for fix in fixes:
                print(f"  • {fix}")
        
        # Re-validate to show remaining issues
        collected_data = collector.collect()
        diagnostics = checker.check(collected_data)
```

## Summary Display

The check command summary includes fixable count:

```python
# In Checker.format_diagnostics()
fixable = [d for d in diagnostics if d.fixable]
if fixable:
    lines.append(f"  Possible fixes: {len(fixable)}")
```

## Error Handling

- **Invalid YAML**: Skip fixing if existing frontmatter can't be parsed
- **Missing Files**: Skip if file doesn't exist at expected path
- **Write Permissions**: Propagate OS errors to user
- **Malformed Diagnostics**: Gracefully skip if diagnostic message can't be parsed

## Testing Strategy

Three test categories:

1. **Successful Fix** - File with multiple fixable issues
2. **Partial Fix** - File with existing structure needing additions
3. **Unfixable Issues** - Verify non-fixable issues remain

Test fixtures use temporary directories to avoid side effects.

## Performance Considerations

- Files are read/written only once per fix operation
- Diagnostics are grouped by file to minimize I/O
- Re-validation after fixes reuses existing collector/checker instances

## Future Enhancements

1. **Interactive Mode**: Prompt user to confirm each fix
2. **Dry Run**: Show what would be fixed without modifying files
3. **Header Reordering**: Smart reordering of existing headers
4. **Type Correction**: Suggest corrections for type mismatches
5. **Batch Operations**: Fix all files in a directory tree
6. **Fix Templates**: User-defined fix patterns for custom rules