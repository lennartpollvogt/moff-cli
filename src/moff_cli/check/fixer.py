"""Fixer module for automatically fixing documentation issues."""

import re
from pathlib import Path
from typing import Any

import yaml

from ..settings import Settings
from .check import Diagnostic


class Fixer:
    """Handles automatic fixing of documentation issues."""

    def __init__(self, settings: Settings):
        """Initialize the fixer with settings.

        Args:
            settings: The settings object containing validation rules.
        """
        self.settings = settings

    def fix_files(
        self,
        collected_data: dict[str, Any],
        diagnostics: list[Diagnostic]
    ) -> dict[str, list[str]]:
        """Fix issues in multiple files.

        Args:
            collected_data: The collected documentation data.
            diagnostics: List of diagnostics to fix.

        Returns:
            Dictionary mapping file paths to list of applied fixes.
        """
        root_dir = Path(collected_data["root_directory"])
        fixes_applied = {}

        # Group diagnostics by file
        diagnostics_by_file = {}
        for diag in diagnostics:
            if diag.fixable:
                if diag.path not in diagnostics_by_file:
                    diagnostics_by_file[diag.path] = []
                diagnostics_by_file[diag.path].append(diag)

        # Process each file
        for file_path, file_diagnostics in diagnostics_by_file.items():
            # The file_path might include the root directory name as a prefix
            # Remove it if it matches the last component of root_dir
            clean_path = file_path
            root_name = root_dir.name
            if file_path.startswith(root_name + "/"):
                clean_path = file_path[len(root_name) + 1:]

            full_path = root_dir / clean_path
            if not full_path.exists():
                # Try with the original path if cleaned path doesn't exist
                full_path = root_dir / file_path
                if not full_path.exists():
                    continue

            # Find the prefix for this file
            prefix_name = None
            for prefix in collected_data:
                if prefix in ["root_directory", "root", "error"]:
                    continue
                # Check if this is a valid prefix with file data
                if isinstance(collected_data[prefix], dict):
                    # Check if the file path exists in this prefix's files
                    if file_path in collected_data[prefix]:
                        prefix_name = prefix
                        break

            if not prefix_name:
                continue

            # Get the markdown data for this file
            md_data = collected_data[prefix_name][file_path].get("md_list", [])

            # Apply fixes
            applied_fixes = self.fix_file(
                full_path,
                file_diagnostics,
                md_data,
                prefix_name
            )

            if applied_fixes:
                fixes_applied[file_path] = applied_fixes

        return fixes_applied

    def fix_file(
        self,
        file_path: Path,
        diagnostics: list[Diagnostic],
        md_data: list[dict],
        prefix_name: str
    ) -> list[str]:
        """Fix issues in a single file.

        Args:
            file_path: Path to the file to fix.
            diagnostics: List of diagnostics for this file.
            md_data: Parsed markdown data from markdown-to-data.
            prefix_name: The prefix that matched this file.

        Returns:
            List of descriptions of applied fixes.
        """
        applied_fixes = []

        # Read the file content
        content = file_path.read_text(encoding="utf-8")
        lines = content.splitlines(keepends=True)

        # Get prefix configuration
        prefix_config = self.settings.get_prefix_config(prefix_name)
        if not prefix_config:
            return applied_fixes

        # Sort diagnostics by type to apply in correct order
        # First frontmatter, then headers
        frontmatter_diags = [d for d in diagnostics if d.rule.startswith("frontmatter.")]
        header_diags = [d for d in diagnostics if d.rule.startswith("headers.")]

        # Fix frontmatter issues first
        if frontmatter_diags:
            lines, fixes = self._fix_frontmatter_issues(
                lines,
                frontmatter_diags,
                prefix_config,
                md_data
            )
            applied_fixes.extend(fixes)

        # Fix header issues
        if header_diags:
            lines, fixes = self._fix_header_issues(
                lines,
                header_diags,
                prefix_config,
                md_data
            )
            applied_fixes.extend(fixes)

        # Write the fixed content back
        if applied_fixes:
            fixed_content = "".join(lines)
            file_path.write_text(fixed_content, encoding="utf-8")

        return applied_fixes

    def _fix_frontmatter_issues(
        self,
        lines: list[str],
        diagnostics: list[Diagnostic],
        prefix_config: Any,
        md_data: list[dict]
    ) -> tuple[list[str], list[str]]:
        """Fix frontmatter-related issues.

        Args:
            lines: File content as list of lines.
            diagnostics: Frontmatter-related diagnostics.
            prefix_config: Configuration for this prefix.
            md_data: Parsed markdown data.

        Returns:
            Tuple of (fixed lines, list of applied fixes).
        """
        applied_fixes = []

        # Check if we have missing frontmatter entirely
        has_missing_frontmatter = any(
            d.rule == "frontmatter.missing" for d in diagnostics
        )

        if has_missing_frontmatter:
            # Add complete frontmatter block
            lines, fixes = self._add_missing_frontmatter(lines, prefix_config)
            applied_fixes.extend(fixes)
        else:
            # Fix missing fields in existing frontmatter
            missing_field_diags = [
                d for d in diagnostics if d.rule == "frontmatter.missing_field"
            ]
            if missing_field_diags:
                lines, fixes = self._add_missing_frontmatter_fields(
                    lines,
                    missing_field_diags,
                    prefix_config,
                    md_data
                )
                applied_fixes.extend(fixes)

        return lines, applied_fixes

    def _add_missing_frontmatter(
        self,
        lines: list[str],
        prefix_config: Any
    ) -> tuple[list[str], list[str]]:
        """Add complete frontmatter block when missing.

        Args:
            lines: File content as list of lines.
            prefix_config: Configuration for this prefix.

        Returns:
            Tuple of (fixed lines, list of applied fixes).
        """
        applied_fixes = []

        # Build the frontmatter content
        frontmatter_data = {}

        # Add required fields with empty values
        for field, field_type in prefix_config.frontmatter_required.items():
            if field_type == "list":
                frontmatter_data[field] = []
            elif field_type == "object":
                frontmatter_data[field] = {}
            elif field_type == "boolean":
                frontmatter_data[field] = False
            elif field_type == "number":
                frontmatter_data[field] = 0
            else:  # string
                frontmatter_data[field] = ""

        # Add optional fields that are commonly used (with empty values)
        for field, field_type in prefix_config.frontmatter_optional.items():
            if field_type == "list":
                frontmatter_data[field] = []

        # Create YAML frontmatter
        yaml_content = yaml.dump(
            frontmatter_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Insert at the beginning of the file
        new_lines = ["---\n"]
        for line in yaml_content.splitlines(keepends=True):
            new_lines.append(line if line.endswith('\n') else line + '\n')
        new_lines.append("---\n")
        new_lines.append("\n")  # Add blank line after frontmatter

        # Combine with existing content
        new_lines.extend(lines)

        applied_fixes.append("Added missing frontmatter block")
        return new_lines, applied_fixes

    def _add_missing_frontmatter_fields(
        self,
        lines: list[str],
        diagnostics: list[Diagnostic],
        prefix_config: Any,
        md_data: list[dict]
    ) -> tuple[list[str], list[str]]:
        """Add missing fields to existing frontmatter.

        Args:
            lines: File content as list of lines.
            diagnostics: Missing field diagnostics.
            prefix_config: Configuration for this prefix.
            md_data: Parsed markdown data.

        Returns:
            Tuple of (fixed lines, list of applied fixes).
        """
        applied_fixes = []

        # Find frontmatter boundaries
        frontmatter_start = -1
        frontmatter_end = -1

        for i, line in enumerate(lines):
            if line.strip() == "---":
                if frontmatter_start == -1:
                    frontmatter_start = i
                else:
                    frontmatter_end = i
                    break

        if frontmatter_start == -1 or frontmatter_end == -1:
            # No valid frontmatter found, shouldn't happen if diagnostics are correct
            return lines, applied_fixes

        # Parse existing frontmatter
        frontmatter_lines = lines[frontmatter_start + 1:frontmatter_end]
        frontmatter_text = "".join(frontmatter_lines)

        try:
            existing_data = yaml.safe_load(frontmatter_text) or {}
        except yaml.YAMLError:
            # Can't parse existing frontmatter, skip fixing
            return lines, applied_fixes

        # Add missing fields
        missing_fields = []
        for diag in diagnostics:
            if diag.rule == "frontmatter.missing_field":
                # Extract field name from message
                match = re.search(r"field '(\w+)'", diag.message)
                if match:
                    field = match.group(1)
                    missing_fields.append(field)

        for field in missing_fields:
            # Determine field type
            field_type = prefix_config.frontmatter_required.get(field)
            if not field_type:
                field_type = prefix_config.frontmatter_optional.get(field)

            if field_type:
                if field_type == "list":
                    existing_data[field] = []
                elif field_type == "object":
                    existing_data[field] = {}
                elif field_type == "boolean":
                    existing_data[field] = False
                elif field_type == "number":
                    existing_data[field] = 0
                else:  # string
                    existing_data[field] = ""

                applied_fixes.append(f"Added missing frontmatter field: {field}")

        # Generate new frontmatter
        new_yaml = yaml.dump(
            existing_data,
            default_flow_style=False,
            allow_unicode=True,
            sort_keys=False
        )

        # Replace old frontmatter with new
        new_lines = lines[:frontmatter_start + 1]
        for line in new_yaml.splitlines(keepends=True):
            new_lines.append(line if line.endswith('\n') else line + '\n')
        new_lines.extend(lines[frontmatter_end:])

        return new_lines, applied_fixes

    def _fix_header_issues(
        self,
        lines: list[str],
        diagnostics: list[Diagnostic],
        prefix_config: Any,
        md_data: list[dict]
    ) -> tuple[list[str], list[str]]:
        """Fix header-related issues.

        Args:
            lines: File content as list of lines.
            diagnostics: Header-related diagnostics.
            prefix_config: Configuration for this prefix.
            md_data: Parsed markdown data.

        Returns:
            Tuple of (fixed lines, list of applied fixes).
        """
        applied_fixes = []

        # First, fix wrong header levels
        wrong_level_diags = [d for d in diagnostics if "wrong_level" in d.rule]
        if wrong_level_diags:
            lines, fixes = self._fix_wrong_header_levels(
                lines,
                wrong_level_diags,
                prefix_config,
                md_data
            )
            applied_fixes.extend(fixes)

        # Then, add missing headers
        missing_header_diags = [d for d in diagnostics if d.rule == "headers.missing"]
        if missing_header_diags:
            lines, fixes = self._add_missing_headers(
                lines,
                missing_header_diags,
                prefix_config,
                md_data
            )
            applied_fixes.extend(fixes)

        return lines, applied_fixes

    def _fix_wrong_header_levels(
        self,
        lines: list[str],
        diagnostics: list[Diagnostic],
        prefix_config: Any,
        md_data: list[dict]
    ) -> tuple[list[str], list[str]]:
        """Fix headers with wrong levels.

        Args:
            lines: File content as list of lines.
            diagnostics: Wrong level diagnostics.
            prefix_config: Configuration for this prefix.
            md_data: Parsed markdown data.

        Returns:
            Tuple of (fixed lines, list of applied fixes).
        """
        applied_fixes = []

        # Get existing headers from md_data
        headers = [item for item in md_data if "header" in item]

        for diag in diagnostics:
            # Extract the expected level and text from the diagnostic message
            match = re.search(r"level=(\d+) text='([^']+)'", diag.message)
            if not match:
                continue

            expected_level = int(match.group(1))
            header_text = match.group(2)

            # Find the header in the file
            for i, line in enumerate(lines):
                if line.strip().endswith(header_text):
                    # Check if it's a header line
                    header_match = re.match(r'^(#+)\s+(.+)$', line)
                    if header_match and header_match.group(2).strip() == header_text:
                        current_level = len(header_match.group(1))
                        if current_level != expected_level:
                            # Fix the level
                            new_prefix = "#" * expected_level
                            lines[i] = f"{new_prefix} {header_text}\n"
                            applied_fixes.append(
                                f"Fixed header level for '{header_text}' from {current_level} to {expected_level}"
                            )
                            break

        return lines, applied_fixes

    def _add_missing_headers(
        self,
        lines: list[str],
        diagnostics: list[Diagnostic],
        prefix_config: Any,
        md_data: list[dict]
    ) -> tuple[list[str], list[str]]:
        """Add missing headers at correct positions.

        Args:
            lines: File content as list of lines.
            diagnostics: Missing header diagnostics.
            prefix_config: Configuration for this prefix.
            md_data: Parsed markdown data.

        Returns:
            Tuple of (fixed lines, list of applied fixes).
        """
        applied_fixes = []

        # Extract required headers from diagnostics
        missing_headers = []
        for diag in diagnostics:
            match = re.search(r"level=(\d+) text='([^']+)'", diag.message)
            if match:
                level = int(match.group(1))
                text = match.group(2)
                missing_headers.append({"level": level, "text": text})

        # Get existing headers to determine insertion points
        existing_headers = []
        for i, line in enumerate(lines):
            header_match = re.match(r'^(#+)\s+(.+)$', line)
            if header_match:
                existing_headers.append({
                    "level": len(header_match.group(1)),
                    "text": header_match.group(2).strip(),
                    "line_index": i
                })

        # Get the required headers from config to maintain order
        required_headers = prefix_config.headers_required

        # Determine where to insert each missing header
        insertions = []  # List of (line_index, header_content) tuples

        for req_header in required_headers:
            # Check if this header is missing
            is_missing = any(
                h["level"] == req_header.level and h["text"] == req_header.text
                for h in missing_headers
            )

            if is_missing:
                # Find the best insertion point
                insert_index = self._find_header_insertion_point(
                    req_header,
                    required_headers,
                    existing_headers,
                    lines
                )

                header_content = "#" * req_header.level + " " + req_header.text + "\n"
                insertions.append((insert_index, header_content))
                applied_fixes.append(f"Added missing header: {req_header.text}")

        # Sort insertions by index in reverse order to maintain correct positions
        insertions.sort(key=lambda x: x[0], reverse=True)

        # Apply insertions
        for insert_index, header_content in insertions:
            # Add a blank line before the header if needed
            if insert_index > 0 and lines[insert_index - 1].strip():
                lines.insert(insert_index, "\n")
                lines.insert(insert_index + 1, header_content)
            else:
                lines.insert(insert_index, header_content)

            # Add a blank line after the header
            lines.insert(insert_index + 1, "\n")

        return lines, applied_fixes

    def _find_header_insertion_point(
        self,
        target_header: Any,
        required_headers: list[Any],
        existing_headers: list[dict],
        lines: list[str]
    ) -> int:
        """Find the best position to insert a missing header.

        Args:
            target_header: The header to insert.
            required_headers: All required headers from config.
            existing_headers: Existing headers in the file.
            lines: File content as list of lines.

        Returns:
            Line index where the header should be inserted.
        """
        # Find the position of the target header in the required list
        target_index = -1
        for i, req in enumerate(required_headers):
            if req.level == target_header.level and req.text == target_header.text:
                target_index = i
                break

        if target_index == -1:
            # Not found in required headers, shouldn't happen
            return len(lines)

        # Find the nearest existing required header before our target
        insert_after_line = -1
        for i in range(target_index - 1, -1, -1):
            prev_req = required_headers[i]
            for existing in existing_headers:
                if (existing["level"] == prev_req.level and
                    existing["text"] == prev_req.text):
                    insert_after_line = existing["line_index"]
                    break
            if insert_after_line != -1:
                break

        # Find the nearest existing required header after our target
        insert_before_line = len(lines)
        for i in range(target_index + 1, len(required_headers)):
            next_req = required_headers[i]
            for existing in existing_headers:
                if (existing["level"] == next_req.level and
                    existing["text"] == next_req.text):
                    insert_before_line = existing["line_index"]
                    break
            if insert_before_line < len(lines):
                break

        # Determine the best insertion point
        if insert_after_line != -1:
            # Insert after the previous required header
            # Find the end of the section (next header or end of file)
            insert_line = insert_after_line + 1
            while insert_line < len(lines) and insert_line < insert_before_line:
                if re.match(r'^#+\s+', lines[insert_line]):
                    break
                insert_line += 1
            return insert_line
        else:
            # Insert at the beginning (after frontmatter if present)
            insert_line = 0

            # Skip frontmatter if present
            if lines and lines[0].strip() == "---":
                in_frontmatter = True
                insert_line = 1
                while insert_line < len(lines):
                    if lines[insert_line].strip() == "---":
                        insert_line += 1
                        # Skip any blank lines after frontmatter
                        while insert_line < len(lines) and not lines[insert_line].strip():
                            insert_line += 1
                        break
                    insert_line += 1

            return min(insert_line, insert_before_line)
