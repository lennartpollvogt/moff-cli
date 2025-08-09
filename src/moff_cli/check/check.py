"""Check module for moff-cli.

This module validates collected documentation against the rules defined in settings.json.
It ensures files are in allowed locations, frontmatter conforms to schema, and required
headers are present in the correct order.
"""

import re
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Any

from ..settings import HeaderMatch, HeaderOrder, LocationConstraint, Settings


class Severity(str, Enum):
    """Severity levels for validation issues."""
    ERROR = "error"
    WARNING = "warning"
    INFO = "info"


class RuleCategory(str, Enum):
    """Categories of validation rules."""
    ROOT = "root"
    LOCATION = "location"
    FRONTMATTER = "frontmatter"
    HEADERS = "headers"


class Diagnostic:
    """Represents a validation diagnostic."""

    def __init__(
        self,
        path: str,
        prefix: str,
        rule: str,
        message: str,
        severity: Severity = Severity.ERROR,
        line: int | None = None
    ):
        """Initialize a diagnostic.

        Args:
            path: File path relative to root.
            prefix: The prefix that matched this file.
            rule: The rule category and specific rule (e.g., "headers.missing").
            message: Human-readable diagnostic message.
            severity: Severity level of the issue.
            line: Optional line number for the issue.
        """
        self.path = path
        self.prefix = prefix
        self.rule = rule
        self.message = message
        self.severity = severity
        self.line = line

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "path": self.path,
            "prefix": self.prefix,
            "rule": self.rule,
            "message": self.message,
            "severity": self.severity.value,
            "line": self.line
        }

    def __str__(self) -> str:
        """String representation for console output."""
        line_info = f" (line {self.line})" if self.line else ""
        return f"{self.path}{line_info}: [{self.severity.value}] {self.message}"


class Checker:
    """Validates documentation against configured rules."""

    def __init__(self, settings: Settings):
        """Initialize the checker with settings.

        Args:
            settings: The Settings object containing validation rules.
        """
        self.settings = settings
        self.diagnostics: list[Diagnostic] = []
        self.total_files_checked: int = 0

    def check(self, collected_data: dict[str, Any]) -> list[Diagnostic]:
        """Perform validation on collected documentation.

        Args:
            collected_data: Output from the Collector module.

        Returns:
            List of diagnostics found during validation.
        """
        self.diagnostics = []
        self.total_files_checked = 0

        # Check for collection errors
        if collected_data.get("error"):
            self.diagnostics.append(
                Diagnostic(
                    path="",
                    prefix="",
                    rule="root.error",
                    message=collected_data["error"],
                    severity=Severity.ERROR
                )
            )
            return self.diagnostics

        # Validate root conditions
        self._check_root_conditions(collected_data)

        # Validate each file
        for prefix_name in self.settings.get_all_prefixes():
            if prefix_name in collected_data:
                files = collected_data[prefix_name]
                prefix_config = self.settings.get_prefix_config(prefix_name)

                for file_path, file_data in files.items():
                    self.total_files_checked += 1
                    self._validate_file(
                        file_path,
                        file_data,
                        prefix_name,
                        prefix_config
                    )

        # Sort diagnostics for deterministic output
        self.diagnostics.sort(key=lambda d: (d.path, d.line or 0, d.rule))

        return self.diagnostics

    def _check_root_conditions(self, collected_data: dict[str, Any]) -> None:
        """Check root-level conditions.

        Args:
            collected_data: Output from the Collector module.
        """
        root_info = collected_data.get("root", {})

        # Check for multiple root candidates
        if root_info.get("additional_root_candidates"):
            candidates = root_info["additional_root_candidates"]
            self.diagnostics.append(
                Diagnostic(
                    path="",
                    prefix="",
                    rule="root.multiple_candidates",
                    message=f"Multiple root candidates found: {', '.join(candidates)}",
                    severity=Severity.ERROR
                )
            )

        # Check for missing project file
        project_files = collected_data.get("project", {})
        if not project_files:
            self.diagnostics.append(
                Diagnostic(
                    path="",
                    prefix="project",
                    rule="root.missing_project",
                    message="No project file found in root directory",
                    severity=Severity.ERROR
                )
            )

    def _validate_file(
        self,
        file_path: str,
        file_data: dict[str, Any],
        prefix_name: str,
        prefix_config: Any
    ) -> None:
        """Validate a single file against its prefix configuration.

        Args:
            file_path: Path to the file relative to root.
            file_data: File data including is_in_root and md_list.
            prefix_name: Name of the prefix.
            prefix_config: Configuration for this prefix.
        """
        # Validate location constraint
        self._validate_location(file_path, file_data, prefix_name, prefix_config)

        # Get md_list for further validation
        md_list = file_data.get("md_list", [])

        # Check for parsing errors
        if md_list and isinstance(md_list[0], dict) and "error" in md_list[0]:
            self.diagnostics.append(
                Diagnostic(
                    path=file_path,
                    prefix=prefix_name,
                    rule="parsing.error",
                    message=md_list[0]["error"],
                    severity=Severity.ERROR
                )
            )
            return

        # Validate frontmatter
        self._validate_frontmatter(file_path, md_list, prefix_name, prefix_config)

        # Validate headers
        self._validate_headers(file_path, md_list, prefix_name, prefix_config)

    def _validate_location(
        self,
        file_path: str,
        file_data: dict[str, Any],
        prefix_name: str,
        prefix_config: Any
    ) -> None:
        """Validate file location constraints.

        Args:
            file_path: Path to the file.
            file_data: File data including is_in_root.
            prefix_name: Name of the prefix.
            prefix_config: Configuration for this prefix.
        """
        is_in_root = file_data.get("is_in_root", False)
        location_constraint = prefix_config.location

        if location_constraint == LocationConstraint.ROOT_ONLY and not is_in_root:
            self.diagnostics.append(
                Diagnostic(
                    path=file_path,
                    prefix=prefix_name,
                    rule="location.root_only",
                    message="File must be in root directory",
                    severity=Severity.ERROR
                )
            )
        elif location_constraint == LocationConstraint.SUBDIRS_ONLY and is_in_root:
            self.diagnostics.append(
                Diagnostic(
                    path=file_path,
                    prefix=prefix_name,
                    rule="location.subdirs_only",
                    message="File must be in a subdirectory, not in root",
                    severity=Severity.ERROR
                )
            )

    def _validate_frontmatter(
        self,
        file_path: str,
        md_list: list[dict[str, Any]],
        prefix_name: str,
        prefix_config: Any
    ) -> None:
        """Validate frontmatter against schema.

        Args:
            file_path: Path to the file.
            md_list: Parsed markdown content.
            prefix_name: Name of the prefix.
            prefix_config: Configuration for this prefix.
        """
        # Find metadata in md_list
        metadata = None
        metadata_line = None
        for item in md_list:
            if "metadata" in item:
                metadata = item["metadata"]
                metadata_line = item.get("start_line")
                break

        # Check if metadata is required
        if not metadata and prefix_config.frontmatter_required:
            self.diagnostics.append(
                Diagnostic(
                    path=file_path,
                    prefix=prefix_name,
                    rule="frontmatter.missing",
                    message="Required frontmatter is missing",
                    severity=Severity.ERROR,
                    line=1
                )
            )
            return

        if metadata:
            # Validate required fields
            for field, expected_type in prefix_config.frontmatter_required.items():
                if field not in metadata:
                    self.diagnostics.append(
                        Diagnostic(
                            path=file_path,
                            prefix=prefix_name,
                            rule="frontmatter.missing_field",
                            message=f"Required frontmatter field '{field}' is missing",
                            severity=Severity.ERROR,
                            line=metadata_line
                        )
                    )
                elif not self.settings.validate_frontmatter_type(metadata[field], expected_type):
                    actual_type = type(metadata[field]).__name__
                    self.diagnostics.append(
                        Diagnostic(
                            path=file_path,
                            prefix=prefix_name,
                            rule="frontmatter.type_mismatch",
                            message=f"Field '{field}' has wrong type: expected {expected_type}, got {actual_type}",
                            severity=Severity.ERROR,
                            line=metadata_line
                        )
                    )

            # Validate optional fields (if present)
            for field, expected_type in prefix_config.frontmatter_optional.items():
                if field in metadata:
                    if not self.settings.validate_frontmatter_type(metadata[field], expected_type):
                        actual_type = type(metadata[field]).__name__
                        self.diagnostics.append(
                            Diagnostic(
                                path=file_path,
                                prefix=prefix_name,
                                rule="frontmatter.type_mismatch",
                                message=f"Optional field '{field}' has wrong type: expected {expected_type}, got {actual_type}",
                                severity=Severity.ERROR,
                                line=metadata_line
                            )
                        )

    def _validate_headers(
        self,
        file_path: str,
        md_list: list[dict[str, Any]],
        prefix_name: str,
        prefix_config: Any
    ) -> None:
        """Validate headers against rules.

        Args:
            file_path: Path to the file.
            md_list: Parsed markdown content.
            prefix_name: Name of the prefix.
            prefix_config: Configuration for this prefix.
        """
        # Extract headers from md_list
        headers = []
        for item in md_list:
            if "header" in item:
                header_info = item["header"]
                headers.append({
                    "level": header_info.get("level"),
                    "content": header_info.get("content", ""),
                    "line": item.get("start_line")
                })

        # Check required headers
        required_headers = prefix_config.headers_required
        if not required_headers:
            return

        # Track which required headers were found and their positions
        found_positions = []

        for req_header in required_headers:
            found = False
            position = -1

            for i, header in enumerate(headers):
                if header["level"] != req_header.level:
                    continue

                # Check text match
                if req_header.match == HeaderMatch.EXACT:
                    if header["content"] == req_header.text:
                        found = True
                        position = i
                        break
                elif req_header.match == HeaderMatch.REGEX:
                    if re.match(req_header.text, header["content"]):
                        found = True
                        position = i
                        break

            if not found:
                self.diagnostics.append(
                    Diagnostic(
                        path=file_path,
                        prefix=prefix_name,
                        rule="headers.missing",
                        message=f"Missing required header level={req_header.level} text='{req_header.text}'",
                        severity=Severity.ERROR
                    )
                )
            else:
                found_positions.append(position)

        # Check header order if all required headers were found
        if len(found_positions) == len(required_headers) and len(found_positions) > 1:
            order = prefix_config.headers_order

            if order == HeaderOrder.STRICT:
                # Headers must be in exact order with no other required headers between
                for i in range(1, len(found_positions)):
                    if found_positions[i] <= found_positions[i-1]:
                        self.diagnostics.append(
                            Diagnostic(
                                path=file_path,
                                prefix=prefix_name,
                                rule="headers.order",
                                message="Required headers are not in strict order",
                                severity=Severity.ERROR,
                                line=headers[found_positions[i]]["line"] if found_positions[i] < len(headers) else None
                            )
                        )
                        break

            elif order == HeaderOrder.IN_ORDER:
                # Headers must appear in order but other headers can be between
                for i in range(1, len(found_positions)):
                    if found_positions[i] <= found_positions[i-1]:
                        self.diagnostics.append(
                            Diagnostic(
                                path=file_path,
                                prefix=prefix_name,
                                rule="headers.order",
                                message="Required headers are not in order",
                                severity=Severity.ERROR,
                                line=headers[found_positions[i]]["line"] if found_positions[i] < len(headers) else None
                            )
                        )
                        break

    def generate_expected_structure(self, prefix_name: str) -> list[str]:
        """Generate expected structure template for a given prefix.

        Args:
            prefix_name: The prefix name (e.g., 'feature', 'tech', 'project')

        Returns:
            List of lines showing the expected structure.
        """
        lines = []
        prefix_config = self.settings.get_prefix_config(prefix_name)

        if not prefix_config:
            return lines

        # Generate frontmatter template
        has_frontmatter = prefix_config.frontmatter_required or prefix_config.frontmatter_optional
        if has_frontmatter:
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
                # Skip comment fields
                if field.startswith("_"):
                    continue
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

    def format_diagnostics(
        self,
        diagnostics: list[Diagnostic],
        root_directory: Path | None = None,
        use_colors: bool = False,
        include_header: bool = False,
        include_summary: bool = True,
        verbose: bool = False
    ) -> list[str]:
        """Format diagnostics in a human-readable grouped format.

        Args:
            diagnostics: List of diagnostics to format.
            root_directory: Root directory path (for header).
            use_colors: Whether to include color codes (for terminal).
            include_header: Whether to include header with timestamp.
            include_summary: Whether to include summary statistics.
            verbose: Whether to include expected structure templates for files with errors.

        Returns:
            List of formatted strings (lines).
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

        # Add summary if requested
        if include_summary:
            total_issues = len(diagnostics)
            errors = [d for d in diagnostics if d.severity == Severity.ERROR]
            warnings = [d for d in diagnostics if d.severity == Severity.WARNING]
            info_msgs = [d for d in diagnostics if d.severity == Severity.INFO]

            lines.append("Summary:")
            lines.append(f"  Files checked: {self.total_files_checked}")
            lines.append(f"  Total issues: {total_issues}")
            if errors:
                lines.append(f"  Errors: {len(errors)}")
            if warnings:
                lines.append(f"  Warnings: {len(warnings)}")
            if info_msgs:
                lines.append(f"  Info: {len(info_msgs)}")

            if not diagnostics:
                lines.extend([
                    "",
                    "✓ All checks passed!",
                    "No validation issues found."
                ])
                return lines

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

                # Sort diagnostics within each file for deterministic output
                file_diags = sorted(by_file[file_path], key=lambda d: (d.line or 0, d.rule))

                for diag in file_diags:
                    severity = diag.severity.value
                    line_info = f" (line {diag.line})" if diag.line else ""

                    # Format the diagnostic line
                    diag_line = f"  {severity}  {diag.rule}: {diag.message}{line_info}"
                    lines.append(diag_line)

                # Add expected structure in verbose mode
                if verbose and by_file[file_path]:
                    # Get the prefix from the first diagnostic of this file
                    first_diag = by_file[file_path][0]
                    if first_diag.prefix:
                        expected_structure = self.generate_expected_structure(first_diag.prefix)
                        if expected_structure:
                            lines.append("")
                            lines.append(f"  Expected structure for this file type ({first_diag.prefix}):")
                            for struct_line in expected_structure:
                                lines.append(f"  {struct_line}")

        return lines

    def save_results(self, root_directory: Path, diagnostics: list[Diagnostic], verbose: bool = False) -> Path:
        """Save validation results to moff_results.txt.

        Args:
            root_directory: Root directory where to save the results file.
            diagnostics: List of diagnostics to save.
            verbose: Whether to include expected structure templates for files with errors.

        Returns:
            Path to the saved results file.
        """
        results_path = root_directory / "moff_results.txt"

        # Use the unified formatter to get formatted lines
        lines = self.format_diagnostics(
            diagnostics,
            root_directory=root_directory,
            use_colors=False,  # No colors in file output
            include_header=True,
            include_summary=True,
            verbose=verbose  # Pass verbose flag for expected structure templates
        )

        # Write to file
        with open(results_path, 'w', encoding='utf-8') as f:
            # Remove any trailing empty lines
            while lines and lines[-1] == "":
                lines.pop()
            f.write('\n'.join(lines))
            f.write('\n')  # Add final newline

        return results_path

    def get_exit_code(self, diagnostics: list[Diagnostic]) -> int:
        """Determine exit code based on diagnostics.

        Args:
            diagnostics: List of diagnostics.

        Returns:
            0 if no errors, non-zero otherwise.
        """
        has_errors = any(d.severity == Severity.ERROR for d in diagnostics)
        return 1 if has_errors else 0
