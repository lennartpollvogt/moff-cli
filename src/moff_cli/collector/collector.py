"""Collector module for moff-cli.

This module handles discovering the documentation root and collecting all
markdown files, parsing them with markdown-to-data library.
"""

import fnmatch
from pathlib import Path
from typing import Any

from markdown_to_data import Markdown

from ..settings import Settings


class Collector:
    """Collects and parses markdown files based on settings configuration."""

    def __init__(self, settings: Settings, start_path: Path | None = None):
        """Initialize the collector with settings.

        Args:
            settings: The Settings object containing configuration.
            start_path: Optional starting path for root detection. Defaults to current directory.
        """
        self.settings = settings
        self.start_path = start_path or Path.cwd()

    def collect(self) -> dict[str, Any]:
        """Collect all markdown files according to settings.

        Returns:
            Dictionary containing root info and grouped markdown files by prefix.
        """
        # Step 1: Determine the documentation root
        root_info = self._find_root()
        if root_info["error"]:
            return {
                "error": root_info["error"],
                "root_directory": None,
                "root": root_info
            }

        root_directory = Path(root_info["root_directory"])

        # Step 2: Traverse and collect markdown files
        all_md_files = self._collect_markdown_files(root_directory)

        # Step 3: Match files to prefixes and parse
        grouped_files = self._group_and_parse_files(all_md_files, root_directory)

        return {
            "root_directory": str(root_directory),
            "root": root_info,
            **grouped_files
        }

    def _find_root(self) -> dict[str, Any]:
        """Find the documentation root directory.

        Returns:
            Dictionary with root detection information.
        """
        root_info = {
            "detection": {
                "method": self.settings.root.detect_method,
                "pattern": self.settings.root.detect_pattern,
                "override_path_used": False
            },
            "root_file": None,
            "additional_root_candidates": [],
            "error": None
        }

        # Check if override path is provided
        if self.settings.root.override_path:
            override_path = Path(self.settings.root.override_path)
            if override_path.exists() and override_path.is_dir():
                root_info["detection"]["override_path_used"] = True
                root_info["root_directory"] = str(override_path.resolve())

                # Still try to find project file in override path
                project_files = list(override_path.glob(self.settings.root.detect_pattern))
                if project_files:
                    root_info["root_file"] = str(project_files[0].relative_to(override_path.parent))

                return root_info
            else:
                root_info["error"] = f"Override path does not exist or is not a directory: {self.settings.root.override_path}"
                return root_info

        # Auto-detect using pattern
        pattern = self.settings.root.detect_pattern
        root_candidates = self._find_files_by_pattern(self.start_path, pattern)

        if not root_candidates:
            root_info["error"] = f"No root file matching pattern '{pattern}' found"
            return root_info

        # Sort for deterministic selection
        root_candidates.sort()

        # Select the first candidate
        chosen_root_file = root_candidates[0]
        root_directory = chosen_root_file.parent

        root_info["root_file"] = str(chosen_root_file)
        root_info["root_directory"] = str(root_directory)

        # Record additional candidates if any
        if len(root_candidates) > 1:
            root_info["additional_root_candidates"] = [
                str(f) for f in root_candidates[1:]
            ]

        return root_info

    def _find_files_by_pattern(self, start_path: Path, pattern: str,
                              max_depth: int = 5) -> list[Path]:
        """Find files matching a pattern, searching from start_path.

        Args:
            start_path: Starting directory for search.
            pattern: Glob pattern to match.
            max_depth: Maximum depth to search.

        Returns:
            List of matching file paths.
        """
        matches = []

        def search_dir(path: Path, depth: int = 0):
            if depth > max_depth:
                return

            # Check if this directory should be ignored
            if self._should_ignore(path, start_path):
                return

            try:
                # Look for matching files in current directory
                for file_path in path.glob(pattern):
                    if file_path.is_file() and not self._should_ignore(file_path, start_path):
                        matches.append(file_path)

                # Recursively search subdirectories
                for subdir in path.iterdir():
                    if subdir.is_dir():
                        search_dir(subdir, depth + 1)
            except PermissionError:
                # Skip directories we can't access
                pass

        search_dir(start_path)
        return matches

    def _should_ignore(self, path: Path, root: Path) -> bool:
        """Check if a path should be ignored based on ignore patterns.

        Args:
            path: Path to check.
            root: Root directory for relative path calculation.

        Returns:
            True if path should be ignored, False otherwise.
        """
        try:
            relative_path = path.relative_to(root)
        except ValueError:
            # Path is not relative to root, don't ignore
            return False

        path_str = str(relative_path)

        for pattern in self.settings.root.ignore_patterns:
            if fnmatch.fnmatch(path_str, pattern):
                return True
            # Also check against full path components
            if fnmatch.fnmatch(str(path), pattern):
                return True
            # Check each part of the path
            for part in path.parts:
                if fnmatch.fnmatch(part, pattern.strip("*/")):
                    return True

        return False

    def _collect_markdown_files(self, root_directory: Path) -> list[Path]:
        """Collect all markdown files from root directory.

        Args:
            root_directory: Root directory to search.

        Returns:
            List of markdown file paths.
        """
        md_files = []

        def walk_directory(directory: Path):
            try:
                for item in directory.iterdir():
                    # Check if should be ignored
                    if self._should_ignore(item, root_directory):
                        continue

                    if item.is_file() and item.suffix == '.md':
                        md_files.append(item)
                    elif item.is_dir():
                        walk_directory(item)
            except PermissionError:
                # Skip directories we can't access
                pass

        walk_directory(root_directory)

        # Sort for deterministic output
        md_files.sort()
        return md_files

    def _group_and_parse_files(self, md_files: list[Path],
                               root_directory: Path) -> dict[str, dict[str, Any]]:
        """Group markdown files by prefix and parse them.

        Args:
            md_files: List of markdown file paths.
            root_directory: Root directory for calculating relative paths.

        Returns:
            Dictionary with prefix names as keys, containing parsed file data.
        """
        grouped = {}

        for file_path in md_files:
            # Calculate relative path from root
            relative_path = file_path.relative_to(root_directory.parent)

            # Check if file is in root directory
            is_in_root = file_path.parent == root_directory

            # Try to match against each prefix pattern
            prefix_matched = None
            for prefix_name, prefix_config in self.settings.prefixes.items():
                pattern = prefix_config.filename_pattern
                if pattern and fnmatch.fnmatch(file_path.name, pattern):
                    prefix_matched = prefix_name
                    break

            # Skip files that don't match any prefix
            if not prefix_matched:
                continue

            # Parse the file with markdown-to-data
            try:
                content = file_path.read_text(encoding='utf-8')
                markdown = Markdown(content)
                md_list = markdown.md_list
            except Exception as e:
                # If parsing fails, include error information
                md_list = [{"error": f"Failed to parse: {str(e)}"}]

            # Initialize prefix group if needed
            if prefix_matched not in grouped:
                grouped[prefix_matched] = {}

            # Add file data to the appropriate prefix group
            grouped[prefix_matched][str(relative_path)] = {
                "is_in_root": is_in_root,
                "md_list": md_list
            }

        # Ensure all configured prefixes are present in output (even if empty)
        for prefix_name in self.settings.prefixes.keys():
            if prefix_name not in grouped:
                grouped[prefix_name] = {}

        return grouped
