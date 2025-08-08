"""Tree module for moff-cli.

This module displays the documentation structure as a tree in the terminal,
showing only directories and markdown files. It can optionally highlight
inconsistencies detected by the check feature.
"""

from pathlib import Path
from typing import Any

from rich.console import Console
from rich.tree import Tree

from ..check import Checker, Diagnostic, Severity
from ..collector import Collector
from ..settings import Settings


class TreeVisualizer:
    """Visualizes documentation structure as a tree."""

    def __init__(self, settings: Settings, console: Console | None = None):
        """Initialize the tree visualizer.

        Args:
            settings: The Settings object containing configuration.
            console: Optional Rich console for output. Creates one if not provided.
        """
        self.settings = settings
        self.console = console or Console()

    def show_tree(
        self,
        collected_data: dict[str, Any],
        diagnostics: list[Diagnostic] | None = None,
        show_only_errors: bool = False
    ) -> None:
        """Display the documentation tree structure.

        Args:
            collected_data: Output from the Collector module.
            diagnostics: Optional list of diagnostics to highlight issues.
            show_only_errors: If True, only show files with errors.
        """
        if collected_data.get("error"):
            self.console.print(f"[red]Error: {collected_data['error']}[/red]")
            return

        root_directory = Path(collected_data["root_directory"])

        # Build a set of files with errors for highlighting
        error_files = set()
        warning_files = set()
        if diagnostics:
            for diag in diagnostics:
                if diag.path:
                    if diag.severity == Severity.ERROR:
                        error_files.add(diag.path)
                    elif diag.severity == Severity.WARNING:
                        warning_files.add(diag.path)

        # Create the root tree node
        root_name = root_directory.name
        if root_directory == Path(collected_data["root_directory"]):
            root_name = f"📁 {root_name} [dim](documentation root)[/dim]"

        tree = Tree(root_name)

        # Build file structure from collected data
        all_files = self._get_all_files(collected_data)

        # Filter files if show_only_errors is True
        if show_only_errors and diagnostics:
            all_files = [f for f in all_files if f in error_files or f in warning_files]

        # Build directory structure
        dir_structure = self._build_directory_structure(all_files)

        # Add nodes to tree
        self._add_nodes_to_tree(tree, dir_structure, error_files, warning_files, "")

        # Display the tree
        self.console.print("")
        self.console.print(tree)

        # Show summary if diagnostics are provided
        if diagnostics:
            self._show_summary(len(all_files), len(error_files), len(warning_files))

    def _get_all_files(self, collected_data: dict[str, Any]) -> list[str]:
        """Extract all file paths from collected data.

        Args:
            collected_data: Output from the Collector module.

        Returns:
            List of file paths.
        """
        all_files = []

        for prefix in self.settings.get_all_prefixes():
            if prefix in collected_data:
                files = collected_data[prefix]
                all_files.extend(files.keys())

        return sorted(all_files)

    def _build_directory_structure(self, file_paths: list[str]) -> dict[str, Any]:
        """Build a nested dictionary representing the directory structure.

        Args:
            file_paths: List of file paths.

        Returns:
            Nested dictionary representing the directory structure.
        """
        structure = {}

        for file_path in file_paths:
            parts = Path(file_path).parts
            current = structure

            for i, part in enumerate(parts):
                if i == len(parts) - 1:
                    # It's a file
                    if "_files" not in current:
                        current["_files"] = []
                    current["_files"].append(part)
                else:
                    # It's a directory
                    if part not in current:
                        current[part] = {}
                    current = current[part]

        return structure

    def _add_nodes_to_tree(
        self,
        tree_node: Tree,
        structure: dict[str, Any],
        error_files: set[str],
        warning_files: set[str],
        current_path: str
    ) -> None:
        """Recursively add nodes to the tree.

        Args:
            tree_node: Current tree node to add children to.
            structure: Current level of directory structure.
            error_files: Set of file paths with errors.
            warning_files: Set of file paths with warnings.
            current_path: Current path being processed.
        """
        # Add directories first (sorted)
        directories = sorted([k for k in structure.keys() if not k.startswith("_")])
        for dir_name in directories:
            dir_path = Path(current_path) / dir_name if current_path else dir_name

            # Check if this directory contains any markdown files
            has_md_files = self._has_markdown_files(structure[dir_name])

            if has_md_files:
                # Check if directory has errors
                dir_has_errors = self._directory_has_issues(
                    str(dir_path), structure[dir_name], error_files
                )
                dir_has_warnings = self._directory_has_issues(
                    str(dir_path), structure[dir_name], warning_files
                )

                # Style the directory name
                if dir_has_errors:
                    dir_display = f"📁 [red]{dir_name}[/red]"
                elif dir_has_warnings:
                    dir_display = f"📁 [yellow]{dir_name}[/yellow]"
                else:
                    dir_display = f"📁 {dir_name}"

                # Add directory node and recurse
                dir_node = tree_node.add(dir_display)
                self._add_nodes_to_tree(
                    dir_node,
                    structure[dir_name],
                    error_files,
                    warning_files,
                    str(dir_path)
                )

        # Add files (sorted)
        if "_files" in structure:
            for file_name in sorted(structure["_files"]):
                # Only show markdown files
                if not file_name.endswith('.md'):
                    continue

                file_path = Path(current_path) / file_name if current_path else file_name
                file_path_str = str(file_path).replace("\\", "/")

                # Determine file icon and style based on prefix
                icon = self._get_file_icon(file_name)

                # Style based on errors/warnings
                if file_path_str in error_files:
                    file_display = f"{icon} [red]{file_name}[/red] [dim red]✗[/dim red]"
                elif file_path_str in warning_files:
                    file_display = f"{icon} [yellow]{file_name}[/yellow] [dim yellow]⚠[/dim yellow]"
                else:
                    file_display = f"{icon} [green]{file_name}[/green] [dim green]✓[/dim green]"

                tree_node.add(file_display)

    def _has_markdown_files(self, structure: dict[str, Any]) -> bool:
        """Check if a directory structure contains markdown files.

        Args:
            structure: Directory structure dictionary.

        Returns:
            True if contains markdown files, False otherwise.
        """
        # Check for files at this level
        if "_files" in structure:
            for file_name in structure["_files"]:
                if file_name.endswith('.md'):
                    return True

        # Check subdirectories
        for key, value in structure.items():
            if not key.startswith("_") and isinstance(value, dict):
                if self._has_markdown_files(value):
                    return True

        return False

    def _directory_has_issues(
        self,
        dir_path: str,
        structure: dict[str, Any],
        issue_files: set[str]
    ) -> bool:
        """Check if a directory or its subdirectories contain files with issues.

        Args:
            dir_path: Path to the directory.
            structure: Directory structure.
            issue_files: Set of files with issues.

        Returns:
            True if directory contains files with issues.
        """
        # Check files at this level
        if "_files" in structure:
            for file_name in structure["_files"]:
                file_path = Path(dir_path) / file_name
                if str(file_path).replace("\\", "/") in issue_files:
                    return True

        # Check subdirectories
        for key, value in structure.items():
            if not key.startswith("_") and isinstance(value, dict):
                subdir_path = Path(dir_path) / key
                if self._directory_has_issues(str(subdir_path), value, issue_files):
                    return True

        return False

    def _get_file_icon(self, file_name: str) -> str:
        """Get an icon for a file based on its prefix.

        Args:
            file_name: Name of the file.

        Returns:
            Icon string for the file.
        """
        if file_name.startswith("project_"):
            return "📋"
        elif file_name.startswith("feature_"):
            return "⚡"
        elif file_name.startswith("tech_"):
            return "🔧"
        else:
            return "📄"

    def _show_summary(self, total_files: int, error_count: int, warning_count: int) -> None:
        """Show a summary of the tree visualization.

        Args:
            total_files: Total number of files.
            error_count: Number of files with errors.
            warning_count: Number of files with warnings.
        """
        self.console.print("")
        self.console.print("[bold]Summary:[/bold]")
        self.console.print(f"  Total markdown files: {total_files}")

        if error_count > 0:
            self.console.print(f"  Files with errors: [red]{error_count}[/red]")
        else:
            self.console.print("  Files with errors: [green]0[/green]")

        if warning_count > 0:
            self.console.print(f"  Files with warnings: [yellow]{warning_count}[/yellow]")
        else:
            self.console.print("  Files with warnings: [green]0[/green]")

        if error_count == 0 and warning_count == 0:
            self.console.print("\n[green]✓ All files passed validation![/green]")
        else:
            self.console.print("\n[yellow]Run 'moff check' for detailed diagnostics.[/yellow]")


def display_tree(
    start_path: Path | None = None,
    show_errors: bool = True,
    show_only_errors: bool = False
) -> None:
    """Convenience function to display the documentation tree.

    Args:
        start_path: Optional starting path for root detection.
        show_errors: If True, run validation and highlight errors.
        show_only_errors: If True, only show files with errors.
    """
    console = Console()

    # Load settings
    settings = Settings()

    # Collect documentation
    collector = Collector(settings, start_path=start_path or Path.cwd())
    collected_data = collector.collect()

    if collected_data.get("error"):
        console.print(f"[red]Error: {collected_data['error']}[/red]")
        return

    # Run validation if requested
    diagnostics = None
    if show_errors:
        checker = Checker(settings)
        diagnostics = checker.check(collected_data)

    # Display tree
    visualizer = TreeVisualizer(settings, console)
    visualizer.show_tree(collected_data, diagnostics, show_only_errors)
