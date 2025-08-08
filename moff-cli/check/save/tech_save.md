---
project: moff-cli
feature: save
linked_features: [feature_save.md]
---

# Technical Details

The save feature persists validation results from the check feature to a text file in the documentation root. It formats diagnostics into a human-readable report with timestamps, statistics, and detailed violation listings.

## Dependencies

- `pydantic` - for data models and JSON serialization
- `pathlib` (standard library) - for file path operations
- `datetime` (standard library) - for timestamp generation
- `typing` - for type hints
- check module - provides ValidationResult pydantic model to save

# Implementation Details

## File Writing

```python
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from moff_cli.check import ValidationResult, Diagnostic
import json

def save_results(
    validation_result: ValidationResult,
    root_directory: Path,
    filename: str = "moff_results.txt"
) -> None:
    """
    Save validation results to a text file in the root directory.
    
    Args:
        validation_result: The validation results from check feature
        root_directory: Documentation root where file will be saved
        filename: Name of the output file (default: moff_results.txt)
    
    Raises:
        IOError: If file cannot be written
    """
    output_path = root_directory / filename
    
    try:
        content = format_results(validation_result)
        
        # Write with UTF-8 encoding, overwriting existing file
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
            
    except IOError as e:
        raise IOError(f"Failed to save results to {output_path}: {e}")
```

## Results Formatting

```python
def format_results(validation_result: ValidationResult) -> str:
    """
    Format validation results into a human-readable text report.
    
    Args:
        validation_result: The validation results to format
    
    Returns:
        Formatted string ready to write to file
    """
    lines = []
    
    # Header
    lines.append("moff-cli check results")
    lines.append("=" * 50)
    
    # Timestamp
    timestamp = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S UTC")
    lines.append(f"Generated: {timestamp}")
    
    # Root directory
    lines.append(f"Root: {validation_result.root_directory}")
    lines.append("")
    
    # Summary section
    lines.append("Summary:")
    lines.append("-" * 30)
    lines.append(f"Files checked: {validation_result.files_checked}")
    
    # Use pydantic computed fields for counts
    lines.append(f"Errors: {validation_result.error_count}")
    lines.append(f"Warnings: {validation_result.warning_count}")
    lines.append(f"Info: {validation_result.info_count}")
    lines.append(f"Status: {validation_result.status.upper()}")
    lines.append("")
    
    # Violations section
    if validation_result.diagnostics:
        lines.append("Violations:")
        lines.append("-" * 30)
        
        # Sort diagnostics for deterministic output
        sorted_diagnostics = sort_diagnostics(validation_result.diagnostics)
        
        for diagnostic in sorted_diagnostics:
            line = format_diagnostic(diagnostic)
            lines.append(line)
    else:
        lines.append("No violations found.")
    
    lines.append("")
    lines.append("=" * 50)
    lines.append("End of report")
    
    return "\n".join(lines)
```

## Diagnostic Formatting

```python
def format_diagnostic(diagnostic: Diagnostic) -> str:
    """
    Format a single diagnostic into a text line.
    
    Args:
        diagnostic: The diagnostic to format
    
    Returns:
        Formatted string representation of the diagnostic
    """
    # Severity indicator
    severity_map = {
        "error": "[ERROR]",
        "warning": "[WARNING]",
        "info": "[INFO]"
    }
    severity_text = severity_map.get(diagnostic.severity, "[UNKNOWN]")
    
    # Build file reference
    file_ref = str(diagnostic.path)
    if diagnostic.line:
        file_ref += f":{diagnostic.line}"
    
    # Format: [SEVERITY] path/to/file.md:line | rule.category | Message
    parts = [
        severity_text,
        file_ref,
        "|",
        diagnostic.rule,
        "|",
        diagnostic.message
    ]
    
    return " ".join(parts)
```

## Sorting and Determinism

```python
def sort_diagnostics(diagnostics: List[Diagnostic]) -> List[Diagnostic]:
    """
    Sort diagnostics for deterministic output.
    
    Sorting order:
    1. By file path (alphabetical)
    2. By line number (if available)
    3. By rule name
    4. By severity (errors first, then warnings, then info)
    
    Args:
        diagnostics: List of diagnostics to sort
    
    Returns:
        Sorted list of diagnostics
    """
    severity_order = {"error": 0, "warning": 1, "info": 2}
    
    return sorted(
        diagnostics,
        key=lambda d: (
            str(d.path),  # Convert Path to string for sorting
            d.line if d.line is not None else 999999,
            d.rule,
            severity_order.get(d.severity, 999)
        )
    )
```

## Alternative Format: JSON

```python
def save_results_json(
    validation_result: ValidationResult,
    root_directory: Path,
    filename: str = "moff_results.json"
) -> None:
    """
    Save validation results in JSON format for programmatic consumption.
    
    Args:
        validation_result: The validation results from check feature
        root_directory: Documentation root where file will be saved
        filename: Name of the output file
    """
    output_path = root_directory / filename
    
    # Use pydantic's computed fields for summary
    result_dict = {
        "timestamp": datetime.utcnow().isoformat(),
        "root_directory": str(validation_result.root_directory),
        "files_checked": validation_result.files_checked,
        "status": validation_result.status,
        "summary": {
            "total_diagnostics": len(validation_result.diagnostics),
            "errors": validation_result.error_count,
            "warnings": validation_result.warning_count,
            "info": validation_result.info_count
        },
        "diagnostics": [
            {
                "path": str(d.path),
                "prefix": d.prefix,
                "rule": d.rule,
                "message": d.message,
                "severity": d.severity,
                "line": d.line
            }
            for d in sort_diagnostics(validation_result.diagnostics)
        ]
    }
    
    try:
        # Alternative: Use pydantic's json() method
        # json_content = validation_result.json(indent=2, ensure_ascii=False)
        # But we need custom format with timestamp, so use dict approach
        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(result_dict, f, indent=2, ensure_ascii=False)
    except IOError as e:
        raise IOError(f"Failed to save JSON results to {output_path}: {e}")
```

## Integration with Check

```python
def integrate_with_check(check_result: ValidationResult, save_flag: bool) -> None:
    """
    Called by check feature when --save flag is provided.
    
    Args:
        check_result: The validation result from check
        save_flag: Whether to save the results
    """
    if not save_flag:
        return
    
    root_dir = check_result.root_directory
    
    # Save text format (primary)
    save_results(check_result, root_dir, "moff_results.txt")
    
    # Optionally save JSON format for CI/CD integration
    # save_results_json(check_result, root_dir, "moff_results.json")
```

## Alternative: Direct Pydantic JSON Export

```python
def save_results_pydantic_json(
    validation_result: ValidationResult,
    root_directory: Path,
    filename: str = "moff_results_raw.json"
) -> None:
    """
    Save validation results using pydantic's native JSON serialization.
    This produces a pure representation of the ValidationResult model.
    
    Args:
        validation_result: The pydantic ValidationResult model
        root_directory: Documentation root where file will be saved
        filename: Name of the output file
    """
    output_path = root_directory / filename
    
    try:
        # Use pydantic's built-in JSON serialization
        json_content = validation_result.json(
            indent=2,
            ensure_ascii=False,
            # Include computed fields
            include={"error_count", "warning_count", "info_count"}
        )
        
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(json_content)
            
    except IOError as e:
        raise IOError(f"Failed to save pydantic JSON to {output_path}: {e}")
```

## File Management

```python
def cleanup_old_results(root_directory: Path, keep_count: int = 5) -> None:
    """
    Optional: Keep only the last N result files (for versioning).
    
    Args:
        root_directory: Documentation root directory
        keep_count: Number of result files to keep
    """
    # This could be implemented to rotate result files with timestamps
    # e.g., moff_results_20240115_143022.txt
    pass

def create_backup(output_path: Path) -> None:
    """
    Create a backup of existing results before overwriting.
    
    Args:
        output_path: Path to the results file
    """
    if output_path.exists():
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = output_path.with_suffix(f".{timestamp}.txt")
        output_path.rename(backup_path)
```

## Error Handling

- **Permission denied**: Handle write permission errors gracefully
- **Disk full**: Catch and report disk space issues
- **Invalid path**: Validate root directory exists before writing
- **Encoding issues**: Use UTF-8 with proper error handling
- **Concurrent writes**: Handle multiple moff processes (file locking if needed)

## Output Examples

### Successful validation
```
moff-cli check results
==================================================
Generated: 2024-01-15 14:30:22 UTC
Root: moff-cli/moff-cli

Summary:
------------------------------
Files checked: 10
Errors: 0
Warnings: 0
Info: 0
Status: PASSED

No violations found.

==================================================
End of report
```

### Failed validation
```
moff-cli check results
==================================================
Generated: 2024-01-15 14:30:22 UTC
Root: moff-cli/moff-cli

Summary:
------------------------------
Files checked: 10
Errors: 2
Warnings: 1
Info: 0
Status: FAILED

Violations:
------------------------------
[ERROR] collector/tech_collector.md | location.subdirs_only | File must not be in root directory
[ERROR] tree/feature_tree.md:45 | headers.missing | Missing required header level=2 text='Requirements'
[WARNING] check/feature_check.md:12 | frontmatter.type.linked_features | Invalid type for optional field linked_features: expected list

==================================================
End of report
```

## Performance Considerations

- Write file atomically (write to temp file, then rename) to avoid partial writes
- Minimal memory usage: stream large result sets instead of building entire string
- Async I/O for non-blocking saves in future versions
- Compression option for very large result sets