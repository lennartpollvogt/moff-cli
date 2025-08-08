"""CLI interface for moff-cli.

This module provides the command-line interface for the moff documentation
validation tool.
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from .__version__ import __version__
from .check import Checker, Severity
from .collector import Collector
from .settings import Settings
from .tree import TreeVisualizer

console = Console()


def cmd_check(args: argparse.Namespace) -> int:
    """Execute the check command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (0 for success, non-zero for errors).
    """
    # First, use default settings to find the documentation root
    temp_settings = Settings()
    temp_collector = Collector(temp_settings, start_path=args.path or Path.cwd())

    # Find documentation root (this will fail if no project_*.md exists)
    console.print("[dim]Discovering documentation root...[/dim]")
    collected_data = temp_collector.collect()

    if collected_data.get("error"):
        console.print(f"[red]Error: {collected_data['error']}[/red]")
        return 1

    # Now we know the documentation root
    root_dir = Path(collected_data["root_directory"])
    settings_path = root_dir / "settings.json"

    # Create default settings.json if it doesn't exist
    if not settings_path.exists():
        console.print(f"[yellow]No settings.json found in documentation root: {root_dir}[/yellow]")
        console.print("[yellow]Creating default settings...[/yellow]")
        Settings.create_default_settings_file(root_dir)
        console.print(f"[green]Created: {settings_path}[/green]")

    # Load settings from documentation root
    settings = Settings(settings_path)

    # Re-collect with proper settings
    console.print("[dim]Collecting documentation files...[/dim]")
    collector = Collector(settings, start_path=args.path or Path.cwd())
    collected_data = collector.collect()

    if collected_data.get("error"):
        console.print(f"[red]Error: {collected_data['error']}[/red]")
        return 1

    console.print(f"[dim]Root directory: {root_dir}[/dim]\n")

    # Run validation
    checker = Checker(settings)
    diagnostics = checker.check(collected_data)

    # Display results
    if not diagnostics:
        console.print("[green]✓ All checks passed![/green]")
        console.print("\nNo validation issues found.")
    else:
        # Count by severity
        errors = [d for d in diagnostics if d.severity == Severity.ERROR]
        warnings = [d for d in diagnostics if d.severity == Severity.WARNING]
        info_msgs = [d for d in diagnostics if d.severity == Severity.INFO]

        # Display summary
        console.print("[bold]Validation Summary:[/bold]")
        console.print(f"  Files checked: {checker.total_files_checked}")
        console.print(f"  Total issues: {len(diagnostics)}")
        if errors:
            console.print(f"  [red]Errors: {len(errors)}[/red]")
        if warnings:
            console.print(f"  [yellow]Warnings: {len(warnings)}[/yellow]")
        if info_msgs:
            console.print(f"  [blue]Info: {len(info_msgs)}[/blue]")

        console.print("\n[bold]Issues found:[/bold]")

        # Group diagnostics by file
        by_file = {}
        for diag in diagnostics:
            file_key = diag.path or "[root]"
            if file_key not in by_file:
                by_file[file_key] = []
            by_file[file_key].append(diag)

        # Display diagnostics
        for file_path in sorted(by_file.keys()):
            console.print(f"\n[cyan]{file_path}:[/cyan]")
            for diag in by_file[file_path]:
                severity_color = {
                    Severity.ERROR: "red",
                    Severity.WARNING: "yellow",
                    Severity.INFO: "blue"
                }.get(diag.severity, "white")

                line_info = f" [dim](line {diag.line})[/dim]" if diag.line else ""
                prefix_info = f" [{diag.prefix}]" if diag.prefix else ""
                console.print(
                    f"  [{severity_color}]{diag.severity.value}[/{severity_color}]{prefix_info} "
                    f"{diag.rule}: {diag.message}{line_info}"
                )

    # Save results if requested
    if args.save:
        console.print("\n[yellow]Saving results...[/yellow]")
        results_path = checker.save_results(root_dir, diagnostics)
        console.print(f"[green]Results saved to: {results_path}[/green]")

    # Return appropriate exit code
    return checker.get_exit_code(diagnostics)


def cmd_tree(args: argparse.Namespace) -> int:
    """Execute the tree command.

    Args:
        args: Parsed command-line arguments.

    Returns:
        Exit code (always 0 for tree command).
    """
    # First, use default settings to find the documentation root
    temp_settings = Settings()
    temp_collector = Collector(temp_settings, start_path=args.path or Path.cwd())

    # Find documentation root (this will fail if no project_*.md exists)
    collected_data = temp_collector.collect()

    if collected_data.get("error"):
        console.print(f"[red]Error: {collected_data['error']}[/red]")
        return 1

    # Now we know the documentation root
    root_dir = Path(collected_data["root_directory"])
    settings_path = root_dir / "settings.json"

    # Create default settings.json if it doesn't exist
    if not settings_path.exists():
        console.print(f"[yellow]No settings.json found in documentation root: {root_dir}[/yellow]")
        console.print("[yellow]Creating default settings...[/yellow]")
        Settings.create_default_settings_file(root_dir)
        console.print(f"[green]Created: {settings_path}[/green]")

    # Load settings from documentation root
    settings = Settings(settings_path)

    # Re-collect with proper settings
    collector = Collector(settings, start_path=args.path or Path.cwd())
    collected_data = collector.collect()

    if collected_data.get("error"):
        console.print(f"[red]Error: {collected_data['error']}[/red]")
        return 1

    # Run validation if not disabled
    diagnostics = None
    if not args.no_check:
        checker = Checker(settings)
        diagnostics = checker.check(collected_data)

    # Display tree
    visualizer = TreeVisualizer(settings, console)
    visualizer.show_tree(
        collected_data,
        diagnostics=diagnostics,
        show_only_errors=args.errors_only
    )

    return 0


def main() -> int:
    """Main entry point for the CLI.

    Returns:
        Exit code.
    """
    parser = argparse.ArgumentParser(
        prog="moff",
        description="MOFF - Markdown Organization and Format Framework. "
                    "A tool for validating documentation structure and consistency.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  moff check                    # Run validation checks
  moff check --save            # Run checks and save results
  moff tree                    # Display documentation structure
  moff tree --errors-only      # Show only files with errors

For more information, visit: https://github.com/yourusername/moff-cli
        """
    )

    parser.add_argument(
        "--version",
        action="version",
        version=f"moff {__version__}"
    )

    # Create subparsers for commands
    subparsers = parser.add_subparsers(
        title="commands",
        dest="command",
        help="Available commands"
    )

    # Check command
    parser_check = subparsers.add_parser(
        "check",
        help="Validate documentation against configured rules",
        description="Run validation checks on your documentation files."
    )
    parser_check.add_argument(
        "--save",
        action="store_true",
        help="Save validation results to moff_results.txt"
    )
    parser_check.add_argument(
        "--path",
        type=Path,
        help="Path to documentation root (default: current directory)"
    )
    parser_check.add_argument(
        "-v", "--verbose",
        action="store_true",
        help="Show verbose output"
    )

    # Tree command
    parser_tree = subparsers.add_parser(
        "tree",
        help="Display documentation structure as a tree",
        description="Visualize your documentation structure in a tree format."
    )
    parser_tree.add_argument(
        "--no-check",
        action="store_true",
        help="Skip validation checks (faster, no error highlighting)"
    )
    parser_tree.add_argument(
        "--errors-only",
        action="store_true",
        help="Show only files with validation errors"
    )
    parser_tree.add_argument(
        "--path",
        type=Path,
        help="Path to documentation root (default: current directory)"
    )

    # Parse arguments
    args = parser.parse_args()

    # Show help if no command provided
    if not args.command:
        parser.print_help()
        return 0

    # Execute the appropriate command
    try:
        if args.command == "check":
            return cmd_check(args)
        elif args.command == "tree":
            return cmd_tree(args)
        else:
            parser.print_help()
            return 1
    except KeyboardInterrupt:
        console.print("\n[yellow]Operation cancelled by user.[/yellow]")
        return 130
    except Exception as e:
        console.print(f"\n[red]Error: {e}[/red]")
        if hasattr(args, 'verbose') and args.verbose:
            import traceback
            console.print("\n[dim]Traceback:[/dim]")
            traceback.print_exc()
        return 1


if __name__ == "__main__":
    sys.exit(main())
