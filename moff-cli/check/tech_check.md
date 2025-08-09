---
project: moff-cli
feature: check
linked_features: [feature_check.md]
---

# Technical Details

The check feature validates the documentation structure and content against the rules defined in settings. It processes the collector output, performs various validation checks, and produces diagnostics that can be displayed in the terminal or saved to a file.

## Dependencies

- `pydantic` - for data models, validation, and JSON serialization
- `rich` library - for formatted terminal output with colors and tables
- `pathlib` (standard library) - for path operations
- `typing` - for type hints and data structures
- `re` (standard library) - for regex pattern matching in headers
- `datetime` (standard library) - for timestamps in saved output
- collector module - provides the documentation structure to validate
- settings module - provides the validation rules

# Implementation Details

## Data Models

```python
from pydantic import BaseModel, Field, validator, computed_field
from typing import List, Dict, Optional, Literal, Any
from pathlib import Path

class Diagnostic(BaseModel):
    """Represents a single validation issue"""
    path: Path  # File path relative to root
    prefix: str  # The prefix category (project, feature, tech)
    rule: str  # Rule identifier (e.g., "headers.missing", "location.subdirs_only")
    message: str  # Human-readable error message
    severity: Literal["error", "warning", "info"] = "error"
    line: Optional[int] = Field(None, ge=1)  # Line numbers start at 1
    
    @validator('path')
    def path_must_be_relative(cls, v):
        """Ensure diagnostic paths are relative, not absolute"""
        if v.is_absolute():
            raise ValueError("Diagnostic paths must be relative")
        return v
    
    @validator('rule')
    def rule_format(cls, v):
        """Validate rule follows expected format"""
        if not v or not any(c.isalpha() for c in v):
            raise ValueError("Rule must contain at least one letter")
        return v
    
    class Config:
        # Allow Path objects to be serialized
        json_encoders = {
            Path: str
        }

class ValidationResult(BaseModel):
    """Complete validation result"""
    diagnostics: List[Diagnostic]
    files_checked: int = Field(ge=0)
    root_directory: Path
    status: Literal["passed", "failed"]
    
    @computed_field
    @property
    def error_count(self) -> int:
        """Count of error-level diagnostics"""
        return sum(1 for d in self.diagnostics if d.severity == "error")
    
    @computed_field
    @property
    def warning_count(self) -> int:
        """Count of warning-level diagnostics"""
        return sum(1 for d in self.diagnostics if d.severity == "warning")
    
    @computed_field
    @property
    def info_count(self) -> int:
        """Count of info-level diagnostics"""
        return sum(1 for d in self.diagnostics if d.severity == "info")
    
    @validator('status')
    def status_matches_diagnostics(cls, v, values):
        """Ensure status reflects presence of errors"""
        diagnostics = values.get('diagnostics', [])
        has_errors = any(d.severity == "error" for d in diagnostics)
        if has_errors and v == "passed":
            raise ValueError("Status cannot be 'passed' when errors exist")
        if not has_errors and v == "failed":
            # Allow failed status even without errors (for future use cases)
            pass
        return v
    
    class Config:
        json_encoders = {
            Path: str
        }
```

## Main Validation Pipeline

```python
def check_documentation(
    collector_output: Dict[str, Any],
    settings: Settings
) -> ValidationResult:
    """
    Main entry point for documentation validation.
    
    Args:
        collector_output: Output from the collector feature
        settings: Effective settings with validation rules
    
    Returns:
        ValidationResult containing all diagnostics
    """
    diagnostics = []
    files_checked = 0
    root_directory = Path(collector_output["root_directory"])
    
    # 1. Validate root conditions
    root_diagnostics = validate_root_conditions(collector_output, settings)
    diagnostics.extend(root_diagnostics)
    
    # 2. Validate each prefix group
    for prefix_name, prefix_config in settings.prefixes.items():
        if prefix_name in collector_output:
            prefix_files = collector_output[prefix_name]
            
            for file_path, file_data in prefix_files.items():
                files_checked += 1
                
                # Validate individual file
                file_diagnostics = validate_file(
                    file_path=Path(file_path),
                    file_data=file_data,
                    prefix_name=prefix_name,
                    prefix_config=prefix_config,
                    settings=settings
                )
                diagnostics.extend(file_diagnostics)
    
    # Determine overall status
    has_errors = any(d.severity == "error" for d in diagnostics)
    status = "failed" if has_errors else "passed"
    
    return ValidationResult(
        diagnostics=diagnostics,
        files_checked=files_checked,
        root_directory=root_directory,
        status=status
    )
```

## Root Validation

```python
def validate_root_conditions(
    collector_output: Dict[str, Any],
    settings: Settings
) -> List[Diagnostic]:
    """Validate root-level conditions"""
    diagnostics = []
    root_info = collector_output.get("root", {})
    
    # Check if root file is missing
    if not root_info.get("root_file") and not root_info.get("detection", {}).get("override_path_used"):
        diagnostics.append(Diagnostic(
            path=Path("."),
            prefix="root",
            rule="root.missing",
            message="No project file found to determine documentation root",
            severity="error"
        ))
    
    # Check for multiple root candidates
    additional_candidates = root_info.get("additional_root_candidates", [])
    if additional_candidates:
        diagnostics.append(Diagnostic(
            path=Path("."),
            prefix="root",
            rule="root.multiple",
            message=f"Multiple project files found: {', '.join(additional_candidates)}",
            severity="error"
        ))
    
    # Check if project prefix has files
    project_files = collector_output.get("project", {})
    if not project_files:
        diagnostics.append(Diagnostic(
            path=Path("."),
            prefix="project",
            rule="project.missing",
            message="No project file found in documentation root",
            severity="error"
        ))
    
    return diagnostics
```

## File Validation

```python
def validate_file(
    file_path: Path,
    file_data: Dict[str, Any],
    prefix_name: str,
    prefix_config: PrefixConfig,
    settings: Settings
) -> List[Diagnostic]:
    """Validate a single file against its prefix rules"""
    diagnostics = []
    
    # 1. Location validation
    location_diagnostic = validate_location(
        file_path, file_data, prefix_name, prefix_config
    )
    if location_diagnostic:
        diagnostics.append(location_diagnostic)
    
    # 2. Frontmatter validation
    frontmatter_diagnostics = validate_frontmatter(
        file_path, file_data, prefix_name, prefix_config
    )
    diagnostics.extend(frontmatter_diagnostics)
    
    # 3. Headers validation
    header_diagnostics = validate_headers(
        file_path, file_data, prefix_name, prefix_config
    )
    diagnostics.extend(header_diagnostics)
    
    return diagnostics
```

## Location Validation

```python
def validate_location(
    file_path: Path,
    file_data: Dict[str, Any],
    prefix_name: str,
    prefix_config: PrefixConfig
) -> Optional[Diagnostic]:
    """Validate file location constraints"""
    is_in_root = file_data.get("is_in_root", False)
    location_rule = prefix_config.location
    
    if location_rule == "root_only" and not is_in_root:
        return Diagnostic(
            path=file_path,
            prefix=prefix_name,
            rule="location.root_only",
            message=f"{prefix_name} files must be in the root directory",
            severity="error"
        )
    
    if location_rule == "subdirs_only" and is_in_root:
        return Diagnostic(
            path=file_path,
            prefix=prefix_name,
            rule="location.subdirs_only",
            message=f"{prefix_name} files must not be in the root directory",
            severity="error"
        )
    
    return None
```

## Frontmatter Validation

```python
def validate_frontmatter(
    file_path: Path,
    file_data: Dict[str, Any],
    prefix_name: str,
    prefix_config: PrefixConfig
) -> List[Diagnostic]:
    """Validate frontmatter/metadata requirements"""
    diagnostics = []
    md_list = file_data.get("md_list", [])
    
    # Find metadata in md_list
    metadata = None
    metadata_line = None
    for item in md_list:
        if "metadata" in item:
            metadata = item["metadata"]
            metadata_line = item.get("start_line")
            break
    
    # Check required fields
    for field_name, field_type in prefix_config.frontmatter.required.items():
        if metadata is None:
            diagnostics.append(Diagnostic(
                path=file_path,
                prefix=prefix_name,
                rule="frontmatter.missing",
                message=f"Missing required frontmatter",
                severity="error"
            ))
            break
        
        if field_name not in metadata:
            diagnostics.append(Diagnostic(
                path=file_path,
                prefix=prefix_name,
                rule=f"frontmatter.required.{field_name}",
                message=f"Missing required frontmatter field: {field_name}",
                severity="error",
                line=metadata_line
            ))
        else:
            # Validate type
            type_valid = validate_field_type(metadata[field_name], field_type)
            if not type_valid:
                diagnostics.append(Diagnostic(
                    path=file_path,
                    prefix=prefix_name,
                    rule=f"frontmatter.type.{field_name}",
                    message=f"Invalid type for {field_name}: expected {field_type}",
                    severity="error",
                    line=metadata_line
                ))
    
    # Check optional fields if present
    if metadata and prefix_config.frontmatter.optional:
        for field_name, field_type in prefix_config.frontmatter.optional.items():
            if field_name in metadata:
                type_valid = validate_field_type(metadata[field_name], field_type)
                if not type_valid:
                    diagnostics.append(Diagnostic(
                        path=file_path,
                        prefix=prefix_name,
                        rule=f"frontmatter.type.{field_name}",
                        message=f"Invalid type for optional field {field_name}: expected {field_type}",
                        severity="warning",
                        line=metadata_line
                    ))
    
    return diagnostics

def validate_field_type(value: Any, expected_type: str) -> bool:
    """Check if value matches expected type"""
    type_checks = {
        "string": lambda v: isinstance(v, str),
        "number": lambda v: isinstance(v, (int, float)),
        "boolean": lambda v: isinstance(v, bool),
        "list": lambda v: isinstance(v, list),
        "object": lambda v: isinstance(v, dict)
    }
    
    check_func = type_checks.get(expected_type)
    return check_func(value) if check_func else False
```

## Headers Validation

```python
import re

def validate_headers(
    file_path: Path,
    file_data: Dict[str, Any],
    prefix_name: str,
    prefix_config: PrefixConfig
) -> List[Diagnostic]:
    """Validate header requirements and order"""
    diagnostics = []
    md_list = file_data.get("md_list", [])
    
    # Extract headers from md_list
    headers = []
    for item in md_list:
        if "header" in item:
            headers.append({
                "level": item["header"]["level"],
                "content": item["header"]["content"],
                "line": item.get("start_line")
            })
    
    # Check required headers
    required_headers = prefix_config.headers.required
    order_mode = prefix_config.headers.order
    
    # Find matches for required headers
    matched_indices = []
    for req_header in required_headers:
        match_index = find_header_match(headers, req_header)
        if match_index is None:
            diagnostics.append(Diagnostic(
                path=file_path,
                prefix=prefix_name,
                rule="headers.missing",
                message=f"Missing required header level={req_header.level} text='{req_header.text}'",
                severity="error"
            ))
        else:
            matched_indices.append(match_index)
    
    # Validate order if all required headers are present
    if len(matched_indices) == len(required_headers) and matched_indices:
        if not validate_header_order(matched_indices, order_mode):
            diagnostics.append(Diagnostic(
                path=file_path,
                prefix=prefix_name,
                rule="headers.order",
                message=f"Headers not in required order (mode: {order_mode})",
                severity="error"
            ))
    
    return diagnostics

def find_header_match(headers: List[Dict], required: HeaderRule) -> Optional[int]:
    """Find index of matching header"""
    for i, header in enumerate(headers):
        if header["level"] != required.level:
            continue
        
        if required.match == "exact":
            if header["content"] == required.text:
                return i
        elif required.match == "regex":
            if re.match(required.text, header["content"]):
                return i
    
    return None

def validate_header_order(indices: List[int], order_mode: str) -> bool:
    """Check if header indices follow the order rules"""
    if order_mode == "any":
        return True
    
    if order_mode in ["strict", "in-order"]:
        # Check if indices are in ascending order
        for i in range(1, len(indices)):
            if indices[i] <= indices[i-1]:
                return False
    
    return True
```

## Template Generation

```python
def generate_expected_structure(prefix_name: str, settings: Settings) -> List[str]:
    """
    Generate expected structure template for a given prefix.
    
    Args:
        prefix_name: The prefix name (e.g., 'feature', 'tech', 'project')
        settings: Settings object containing prefix configurations
    
    Returns:
        List of lines showing the expected structure
    
    Example:
        >>> lines = generate_expected_structure("feature", settings)
        >>> print("\n".join(lines))
        ---
        project: 
        feature: 
        linked_features: []
        ---
        
        # Overview
        
        ## Requirements
    """
    lines = []
    prefix_config = settings.get_prefix_config(prefix_name)
    
    if not prefix_config:
        return lines
    
    # Generate frontmatter template
    if prefix_config.frontmatter_required or prefix_config.frontmatter_optional:
        lines.append("---")
        
        # Add required fields
        for field, field_type in prefix_config.frontmatter_required.items():
            if field_type == "string":
                lines.append(f"{field}: ")
            elif field_type == "list":
                lines.append(f"{field}: []")
            else:
                lines.append(f"{field}: ")
        
        # Add optional fields
        for field, field_type in prefix_config.frontmatter_optional.items():
            if not field.startswith("_"):  # Skip comment fields
                if field_type == "string":
                    lines.append(f"{field}: ")
                elif field_type == "list":
                    lines.append(f"{field}: []")
                else:
                    lines.append(f"{field}: ")
        
        lines.append("---")
        lines.append("")
    
    # Generate headers template
    if prefix_config.headers_required:
        for header in prefix_config.headers_required:
            level = header.level
            text = header.text
            lines.append(f"{'#' * level} {text}")
            lines.append("")
    
    return lines
```

## Output Formatting

```python
from rich.console import Console
from rich.table import Table
from typing import List, Optional
from rich.panel import Panel

def format_diagnostics(
    diagnostics: List[Diagnostic],
    root_directory: Optional[Path] = None,
    use_colors: bool = False,
    include_header: bool = False,
    include_summary: bool = True,
    verbose: bool = False,
    settings: Optional[Settings] = None
) -> List[str]:
    """
    Format diagnostics in a human-readable grouped format.
    
    Args:
        diagnostics: List of diagnostics to format
        root_directory: Root directory path (for header)
        use_colors: Whether to include color codes (for terminal)
        include_header: Whether to include header with timestamp
        include_summary: Whether to include summary statistics
        verbose: Whether to include expected structure templates for files with errors
        settings: Settings object needed for generating templates in verbose mode
    
    Returns:
        List of formatted strings (lines)
    
    Example output (verbose mode):
        features/feature_broken.md:
          error  headers.missing: Missing required header level=1 text='Overview'
          error  frontmatter.missing: Required frontmatter is missing (line 1)
          
          Expected structure for this file type (feature):
          ---
          project: 
          feature: 
          ---
          
          # Overview
    """
    lines = []
    
    # Add header if requested
    if include_header:
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
        lines.extend([
            "moff-cli check results",
            f"Generated: {timestamp}",
        ])
        if root_directory:
            lines.append(f"Root: {root_directory}")
        lines.append("")
    
    # Add summary section
    if include_summary:
        # ... summary formatting code ...
        pass
    
    # Group diagnostics by file
    by_file = {}
    for diag in diagnostics:
        file_key = diag.path or "[root]"
        if file_key not in by_file:
            by_file[file_key] = []
        by_file[file_key].append(diag)
    
    # Format grouped diagnostics
    if by_file:
        lines.append("")
        lines.append("Issues found:")
        
        for file_path in sorted(by_file.keys()):
            lines.append("")
            lines.append(f"{file_path}:")
            
            # Sort diagnostics within each file
            file_diags = sorted(by_file[file_path], 
                              key=lambda d: (d.line or 0, d.rule))
            
            for diag in file_diags:
                severity = diag.severity
                line_info = f" (line {diag.line})" if diag.line else ""
                diag_line = f"  {severity}  {diag.rule}: {diag.message}{line_info}"
                lines.append(diag_line)
            
            # Add expected structure in verbose mode
            if verbose and settings and by_file[file_path]:
                # Get the prefix from the first diagnostic of this file
                first_diag = by_file[file_path][0]
                if first_diag.prefix:
                    expected_structure = generate_expected_structure(
                        first_diag.prefix, settings
                    )
                    if expected_structure:
                        lines.append("")
                        lines.append(f"  Expected structure for this file type ({first_diag.prefix}):")
                        for struct_line in expected_structure:
                            lines.append(f"  {struct_line}")
    
    return lines

def display_results(result: ValidationResult) -> None:
    """Display validation results in the terminal"""
    console = Console()
    
    # Header
    console.print(Panel.fit(
        f"[bold]moff check[/bold] - Documentation Validation",
        border_style="blue"
    ))
    
    # Summary
    console.print(f"\nRoot: {result.root_directory}")
    console.print(f"Files checked: {result.files_checked}")
    
    if result.status == "passed":
        console.print("[bold green]✓ All checks passed![/bold green]")
    else:
        # Display diagnostics table
        table = Table(title="Validation Issues", show_header=True)
        table.add_column("Severity", style="bold")
        table.add_column("File")
        table.add_column("Rule")
        table.add_column("Message")
        
        # Sort diagnostics
        sorted_diagnostics = sorted(
            result.diagnostics,
            key=lambda d: (str(d.path), d.line or 0, d.rule)
        )
        
        for diagnostic in sorted_diagnostics:
            severity_style = {
                "error": "red",
                "warning": "yellow",
                "info": "cyan"
            }.get(diagnostic.severity, "white")
            
            file_display = str(diagnostic.path)
            if diagnostic.line:
                file_display += f":{diagnostic.line}"
            
            table.add_row(
                f"[{severity_style}]{diagnostic.severity.upper()}[/{severity_style}]",
                file_display,
                diagnostic.rule,
                diagnostic.message
            )
        
        console.print(table)
        
        # Summary counts using pydantic computed fields
        console.print(f"\n[bold red]Errors: {result.error_count}[/bold red]")
        if result.warning_count > 0:
            console.print(f"[bold yellow]Warnings: {result.warning_count}[/bold yellow]")
        if result.info_count > 0:
            console.print(f"[cyan]Info: {result.info_count}[/cyan]")
```

## CLI Command Handler

```python
def check_command(
    path: Optional[Path] = None,
    save: bool = False,
    quiet: bool = False
) -> int:
    """
    Handle the 'moff check' command.
    
    Args:
        path: Optional path to documentation root
        save: Whether to save results to moff_results.txt
        quiet: Suppress terminal output
        verbose: Whether to show expected structure templates for files with errors
    
    Returns:
        Exit code (0 for success, non-zero for failures)
    """
    from moff_cli.collector import collect_documentation
    from moff_cli.settings import load_settings
    from moff_cli.save import save_results
    
    # Determine root directory
    if path:
        root_dir = path
    else:
        root_dir = auto_detect_root()
    
    # Load settings
    settings = load_settings(root_dir)
    
    # Collect documentation
    collector_output = collect_documentation(settings)
    
    # Run validation
    result = check_documentation(collector_output, settings)
    
    # Display results
    if not quiet:
        display_results(result)
    
    # Save if requested
    if save:
        from moff_cli.save import save_results
        save_results(result, root_dir, verbose=verbose)
        if not quiet:
            console = Console()
            console.print(f"\n[green]Results saved to {root_dir}/moff_results.txt[/green]")
    
    # Return appropriate exit code
    return 0 if result.status == "passed" else 1
```

## Error Handling

- **Missing root**: Clear error message about project file not found
- **Invalid metadata types**: Specific messages about type mismatches
- **Regex errors**: Catch and report invalid regex patterns in settings
- **File access**: Handle permission errors when reading files
- **Partial validation**: Continue checking other files even if one fails
- **Pydantic validation**: Catch ValidationError when creating diagnostics (indicates bug in check logic)

```python
from pydantic import ValidationError

def create_diagnostic_safe(*, path: Path, prefix: str, rule: str, 
                          message: str, severity: str = "error", 
                          line: Optional[int] = None) -> Optional[Diagnostic]:
    """
    Safely create a diagnostic with pydantic validation.
    Returns None if validation fails (logs error for debugging).
    """
    try:
        return Diagnostic(
            path=path,
            prefix=prefix,
            rule=rule,
            message=message,
            severity=severity,
            line=line
        )
    except ValidationError as e:
        # Log validation error - this indicates a bug in our code
        print(f"Warning: Invalid diagnostic data: {e}")
        return None
```

## Performance Considerations

- Process files in parallel for large documentation sets
- Cache compiled regex patterns for header matching
- Early exit option for CI/CD pipelines (fail fast)
- Minimal memory footprint by processing files one at a time
- Sort diagnostics only once before display