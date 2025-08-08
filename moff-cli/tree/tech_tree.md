---
project: moff-cli
feature: tree
linked_features: [feature_tree.md]
---

# Technical Details

The tree feature provides a visual representation of the documentation structure in the terminal, showing directories and markdown files in a tree format. It integrates with the collector to obtain the file structure and optionally with check to highlight validation issues.

## Dependencies

- `rich` library - for terminal output with colors and tree formatting
- `pathlib` (standard library) - for path operations
- `typing` - for type hints
- collector module - for obtaining the documentation structure
- check module (optional) - for validation status

# Implementation Details

## Tree Generation Algorithm

```python
from rich.tree import Tree
from rich.console import Console
from pathlib import Path
from typing import Dict, List, Optional, Set

def generate_tree(collector_output: Dict, check_results: Optional[List[Dict]] = None) -> Tree:
    """
    Generate a Rich Tree object from collector output.

    Args:
        collector_output: Output from the collector feature
        check_results: Optional validation results from check feature

    Returns:
        Rich Tree object ready for display
    """
    root_dir = Path(collector_output["root_directory"])
    root_name = root_dir.name

    # Create main tree
    tree = Tree(f"[bold blue]{root_name}[/bold blue]")

    # Build file path set for efficient lookup
    all_files = set()
    violation_files = set()

    # Collect all markdown files from collector output
    for prefix in ["project", "feature", "tech"]:
        if prefix in collector_output:
            for file_path in collector_output[prefix].keys():
                all_files.add(Path(file_path))

    # Mark files with violations if check results provided
    if check_results:
        for diagnostic in check_results:
            violation_files.add(Path(diagnostic["path"]))

    # Build tree structure
    build_tree_recursive(tree, root_dir, all_files, violation_files)

    return tree
```

## Directory Traversal and Tree Building

```python
def build_tree_recursive(
    parent_node: Tree,
    current_path: Path,
    markdown_files: Set[Path],
    violation_files: Set[Path],
    prefix: str = ""
) -> None:
    """
    Recursively build tree structure.

    Args:
        parent_node: Parent tree node to add children to
        current_path: Current directory path being processed
        markdown_files: Set of all markdown file paths to include
        violation_files: Set of files with validation errors
        prefix: Indentation prefix for proper tree formatting
    """
    # Get all items in current directory
    items = []

    # Collect direct markdown files in this directory
    for file_path in markdown_files:
        if file_path.parent == current_path:
            items.append(("file", file_path))

    # Collect subdirectories that contain markdown files
    subdirs = set()
    for file_path in markdown_files:
        if current_path in file_path.parents and file_path.parent != current_path:
            # Get immediate subdirectory
            relative = file_path.relative_to(current_path)
            subdir = current_path / relative.parts[0]
            subdirs.add(subdir)

    for subdir in subdirs:
        items.append(("dir", subdir))

    # Sort items: directories first, then files, alphabetically
    items.sort(key=lambda x: (x[0] != "dir", x[1].name.lower()))

    # Add items to tree
    for item_type, item_path in items:
        if item_type == "file":
            add_file_node(parent_node, item_path, item_path in violation_files)
        else:
            add_directory_node(parent_node, item_path, markdown_files, violation_files)
```

## Node Formatting

```python
def add_file_node(parent: Tree, file_path: Path, has_violation: bool) -> None:
    """
    Add a file node to the tree with appropriate formatting.

    Args:
        parent: Parent tree node
        file_path: Path to the file
        has_violation: Whether file has validation errors
    """
    filename = file_path.name

    # Determine file prefix and apply color coding
    if filename.startswith("project_"):
        icon = "📄"
        color = "cyan"
    elif filename.startswith("feature_"):
        icon = "📋"
        color = "green"
    elif filename.startswith("tech_"):
        icon = "⚙️"
        color = "yellow"
    else:
        icon = "📝"
        color = "white"

    # Add error indicator if violations exist
    if has_violation:
        formatted_name = f"[red]{icon} {filename} ❌[/red]"
    else:
        formatted_name = f"[{color}]{icon} {filename}[/{color}]"

    parent.add(formatted_name)

def add_directory_node(
    parent: Tree,
    dir_path: Path,
    markdown_files: Set[Path],
    violation_files: Set[Path]
) -> Tree:
    """
    Add a directory node to the tree and recurse into it.

    Args:
        parent: Parent tree node
        dir_path: Path to the directory
        markdown_files: Set of all markdown files
        violation_files: Set of files with violations

    Returns:
        The created directory node
    """
    dir_name = dir_path.name

    # Check if directory contains any violations
    has_violations = any(
        file_path in violation_files
        for file_path in markdown_files
        if dir_path in file_path.parents
    )

    if has_violations:
        formatted_name = f"[bold red]📁 {dir_name}[/bold red]"
    else:
        formatted_name = f"[bold blue]📁 {dir_name}[/bold blue]"

    dir_node = parent.add(formatted_name)

    # Recurse into subdirectory
    build_tree_recursive(dir_node, dir_path, markdown_files, violation_files)

    return dir_node
```

## Display Output

```python
def display_tree(
    collector_output: Dict,
    check_results: Optional[List[Dict]] = None,
    show_stats: bool = True
) -> None:
    """
    Display the documentation tree in the terminal.

    Args:
        collector_output: Output from collector
        check_results: Optional check results for error highlighting
        show_stats: Whether to show statistics summary
    """
    console = Console()

    # Generate tree
    tree = generate_tree(collector_output, check_results)

    # Display tree
    console.print(tree)

    # Display statistics if requested
    if show_stats:
        display_statistics(collector_output, check_results, console)

def display_statistics(
    collector_output: Dict,
    check_results: Optional[List[Dict]],
    console: Console
) -> None:
    """Display summary statistics below the tree."""

    # Count files by prefix
    counts = {}
    total_files = 0

    for prefix in ["project", "feature", "tech"]:
        if prefix in collector_output:
            count = len(collector_output[prefix])
            counts[prefix] = count
            total_files += count

    console.print("\n[bold]Statistics:[/bold]")
    console.print(f"  Total markdown files: {total_files}")

    for prefix, count in counts.items():
        console.print(f"  {prefix.capitalize()} files: {count}")

    if check_results:
        error_count = len([d for d in check_results if d["severity"] == "error"])
        warning_count = len([d for d in check_results if d["severity"] == "warning"])

        console.print(f"\n[bold]Validation:[/bold]")
        if error_count > 0:
            console.print(f"  [red]Errors: {error_count}[/red]")
        if warning_count > 0:
            console.print(f"  [yellow]Warnings: {warning_count}[/yellow]")
        if error_count == 0 and warning_count == 0:
            console.print(f"  [green]✓ All checks passed[/green]")
```

## Integration with Collector

```python
def get_tree_from_collector(root_directory: Path) -> None:
    """
    Main entry point that integrates with collector.

    Args:
        root_directory: The documentation root directory
    """
    from moff_cli.collector import collect_documentation
    from moff_cli.settings import load_settings

    # Load settings
    settings = load_settings(root_directory)

    # Collect documentation
    collector_output = collect_documentation(settings)

    # Display tree
    display_tree(collector_output, check_results=None, show_stats=True)
```

## Integration with Check (Optional)

```python
def get_tree_with_validation(root_directory: Path) -> None:
    """
    Display tree with validation status from check feature.

    Args:
        root_directory: The documentation root directory
    """
    from moff_cli.collector import collect_documentation
    from moff_cli.check import check_documentation
    from moff_cli.settings import load_settings

    # Load settings
    settings = load_settings(root_directory)

    # Collect documentation
    collector_output = collect_documentation(settings)

    # Run validation
    check_results = check_documentation(collector_output, settings)

    # Display tree with validation highlights
    display_tree(collector_output, check_results=check_results, show_stats=True)
```

## CLI Command Handler

```python
def tree_command(
    path: Optional[Path] = None,
    check: bool = False,
    no_stats: bool = False
) -> None:
    """
    Handle the 'moff tree' command.

    Args:
        path: Optional path to documentation root (auto-detect if not provided)
        check: Whether to include validation status
        no_stats: Disable statistics display
    """
    # Determine root directory
    if path:
        root_dir = path
    else:
        root_dir = auto_detect_root()

    # Display tree based on options
    if check:
        get_tree_with_validation(root_dir)
    else:
        get_tree_from_collector(root_dir)
```

## Error Handling

- **No root found**: Display clear error message about missing project file
- **Empty documentation**: Show message when no markdown files are found
- **Permission errors**: Handle directory access issues gracefully
- **Display issues**: Fallback to simple ASCII tree if Unicode not supported

## Performance Considerations

- Use set operations for efficient file lookups
- Cache directory structure to avoid repeated filesystem calls
- Lazy evaluation: Only process directories that contain markdown files
- Limit tree depth option for very large documentation sets
