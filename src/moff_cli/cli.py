"""CLI interface for moff-cli.

This module provides the command-line interface for the moff documentation
validation tool.
"""

import argparse
import sys
from pathlib import Path

from rich.console import Console

from .__version__ import __version__
from .check import Checker
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

    # Display results using the unified formatter
    formatted_lines = checker.format_diagnostics(
        diagnostics,
        root_directory=root_dir,
        use_colors=True,  # We'll add colors manually for terminal
        include_header=False,  # Don't include header for terminal output
        include_summary=True,
        verbose=args.verbose  # Pass verbose flag for expected structure templates
    )

    # Print formatted output with appropriate colors
    for line in formatted_lines:
        # Apply colors based on content
        if line.startswith("Summary:"):
            console.print(f"[bold]{line}[/bold]")
        elif line.startswith("Issues found:"):
            console.print(f"\n[bold]{line}[/bold]")
        elif line.startswith("  Errors:"):
            console.print(f"  [red]Errors: {line.split(':')[1].strip()}[/red]")
        elif line.startswith("  Warnings:"):
            console.print(f"  [yellow]Warnings: {line.split(':')[1].strip()}[/yellow]")
        elif line.startswith("  Info:"):
            console.print(f"  [blue]Info: {line.split(':')[1].strip()}[/blue]")
        elif line.startswith("✓ All checks passed!"):
            console.print(f"[green]{line}[/green]")
        elif line.endswith(":") and not line.startswith("  "):
            # File path headers
            console.print(f"\n[cyan]{line}[/cyan]")
        elif line.startswith("  error"):
            # Error diagnostic
            console.print(f"  [red]error[/red]{line[7:]}")
        elif line.startswith("  warning"):
            # Warning diagnostic
            console.print(f"  [yellow]warning[/yellow]{line[9:]}")
        elif line.startswith("  info"):
            # Info diagnostic
            console.print(f"  [blue]info[/blue]{line[6:]}")
        elif line.startswith("  Expected structure"):
            # Expected structure header for verbose mode
            console.print(f"\n  [dim italic]{line}[/dim italic]")
        elif args.verbose and line.startswith("  ---"):
            # Frontmatter delimiters in verbose mode
            console.print(f"  [dim]{line}[/dim]")
        elif args.verbose and line.startswith("  #"):
            # Headers in verbose mode
            console.print(f"  [dim]{line}[/dim]")
        elif args.verbose and line.startswith("  ") and ":" in line and not line.strip().startswith(("error", "warning", "info")):
            # Frontmatter fields in verbose mode
            console.print(f"  [dim]{line}[/dim]")
        else:
            console.print(line)

    # Save results if requested
    if args.save:
        console.print("\n[yellow]Saving results...[/yellow]")
        results_path = checker.save_results(root_dir, diagnostics, verbose=args.verbose)
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
