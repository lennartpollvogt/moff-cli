"""Tests for the Fixer module."""

import tempfile
from pathlib import Path

import pytest
import yaml

from moff_cli.check import Checker, Fixer
from moff_cli.collector import Collector
from moff_cli.settings import Settings


class TestFixer:
    """Test cases for the Fixer class."""

    def test_fix_missing_frontmatter_and_headers(self):
        """Test fixing a file with missing frontmatter and headers (should pass)."""
        # Create a temporary directory with test files
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file to establish root
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

This is a test project.
""")

            # Create a feature file with missing frontmatter and headers
            feature_file = root / "feature_broken.md"
            feature_file.write_text("""Some content without proper structure.

## Wrong Header

More content here.
""")

            # Load settings and collect files
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()

            # Run checks to get diagnostics
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Filter diagnostics for the feature file
            feature_diags = [d for d in diagnostics if "feature_broken.md" in d.path]

            # Verify we have fixable issues
            fixable = [d for d in feature_diags if d.fixable]
            assert len(fixable) > 0, "Should have fixable issues"

            # Apply fixes
            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Verify fixes were applied
            # The key includes the temp directory name
            fixed_files = [k for k in fixes_applied.keys() if k.endswith("feature_broken.md")]
            assert len(fixed_files) > 0, "feature_broken.md should have fixes applied"
            assert len(fixes_applied[fixed_files[0]]) > 0

            # Read the fixed file
            fixed_content = feature_file.read_text()

            # Verify frontmatter was added
            assert fixed_content.startswith("---\n")

            # Parse the frontmatter
            lines = fixed_content.split("\n")
            fm_end = lines[1:].index("---") + 1
            fm_content = "\n".join(lines[1:fm_end])
            fm_data = yaml.safe_load(fm_content)

            # Verify required fields are present
            assert "project" in fm_data
            assert "feature" in fm_data

            # Verify headers were added
            assert "# Overview" in fixed_content
            assert "## Requirements" in fixed_content

            # Re-run validation to ensure no fixable issues remain
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            diagnostics = checker.check(collected_data)
            feature_diags = [d for d in diagnostics if "feature_broken.md" in d.path]
            fixable = [d for d in feature_diags if d.fixable]
            assert len(fixable) == 0, "Should have no remaining fixable issues"

    def test_fix_partial_missing_fields(self):
        """Test fixing a file with partial missing frontmatter fields (edge case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

Test project.
""")

            # Create a feature file with partial frontmatter
            feature_file = root / "feature_partial.md"
            feature_file.write_text("""---
project: test
---

# Overview

Some content.

## Requirements

Requirements here.
""")

            # Load settings and run checks
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Filter for the feature file
            feature_diags = [d for d in diagnostics if "feature_partial.md" in d.path]

            # Should have missing 'feature' field
            missing_field = [d for d in feature_diags if d.rule == "frontmatter.missing_field"]
            assert len(missing_field) > 0, "Should detect missing 'feature' field"

            # Apply fixes
            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Read fixed content
            fixed_content = feature_file.read_text()

            # Parse frontmatter
            lines = fixed_content.split("\n")
            fm_end = lines[1:].index("---") + 1
            fm_content = "\n".join(lines[1:fm_end])
            fm_data = yaml.safe_load(fm_content)

            # Verify the missing field was added
            assert "feature" in fm_data
            assert fm_data["project"] == "test"  # Original field preserved

            # Verify content after frontmatter is preserved
            assert "# Overview" in fixed_content
            assert "Some content." in fixed_content
            assert "## Requirements" in fixed_content

    def test_unfixable_issues_remain(self):
        """Test that unfixable issues are not fixed and remain as diagnostics (failing case)."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

Test project.
""")

            # Create a tech file in root (should be in subdirs_only)
            tech_file = root / "tech_database.md"
            tech_file.write_text("""---
project: test
---

# Technical Details

Some tech content.

# Implementation Details

Implementation here.
""")

            # Load settings and run checks
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Filter for location constraint violation
            location_diags = [d for d in diagnostics if d.rule.startswith("location.")]
            assert len(location_diags) > 0, "Should have location constraint violation"

            # Verify location issues are not fixable
            fixable_location = [d for d in location_diags if d.fixable]
            assert len(fixable_location) == 0, "Location issues should not be fixable"

            # Apply fixes (should not fix location issues)
            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Re-run validation
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            diagnostics = checker.check(collected_data)

            # Location issues should still exist
            location_diags = [d for d in diagnostics if d.rule.startswith("location.")]
            assert len(location_diags) > 0, "Location constraint violations should remain after fix attempt"

            # The file should still be in the wrong location
            assert tech_file.exists()
            assert tech_file.parent == root


    def test_fix_headers_correct_order(self):
        """Test that missing headers are added in the correct order."""
        import re

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

Test project.
""")

            # Create a feature file with only frontmatter (no headers)
            feature_file = root / "feature_empty.md"
            feature_file.write_text("""---
project: test
feature: empty feature
linked_features: []
---""")

            # Load settings and run checks
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Apply fixes
            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Read fixed content
            fixed_content = feature_file.read_text()

            # Find the positions of the headers
            overview_pos = fixed_content.find("# Overview")
            requirements_pos = fixed_content.find("## Requirements")

            # Verify both headers exist
            assert overview_pos != -1, "Overview header should be added"
            assert requirements_pos != -1, "Requirements header should be added"

            # Verify Overview comes before Requirements
            assert overview_pos < requirements_pos, "Overview should come before Requirements"

            # Verify headers are after frontmatter
            frontmatter_end = fixed_content.find("---", 3)  # Find second ---
            assert overview_pos > frontmatter_end, "Headers should be after frontmatter"

    def test_fix_wrong_header_levels(self):
        """Test that headers with wrong levels are fixed in place."""
        import re

        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

Test project.
""")

            # Create a feature file with headers at wrong levels
            feature_file = root / "feature_wrong_levels.md"
            original_content = """---
project: test
feature: wrong levels
linked_features: []
---

## Overview

This should be level 1.

# Requirements

This should be level 2.
"""
            feature_file.write_text(original_content)

            # Load settings and run checks
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Should detect wrong levels
            header_diags = [d for d in diagnostics if "headers.missing" in d.rule]
            assert len(header_diags) == 2, "Should detect both headers as missing (wrong level)"

            # Apply fixes
            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Read fixed content
            fixed_content = feature_file.read_text()

            # Verify headers are at correct levels using regex for exact matches
            assert re.search(r'^# Overview$', fixed_content, re.MULTILINE), "Overview should be level 1"
            assert re.search(r'^## Requirements$', fixed_content, re.MULTILINE), "Requirements should be level 2"

            # Verify wrong level headers are gone using regex
            assert not re.search(r'^## Overview$', fixed_content, re.MULTILINE), "Level 2 Overview should be replaced"
            assert not re.search(r'^# Requirements$', fixed_content, re.MULTILINE), "Level 1 Requirements should be replaced"

            # Verify content is preserved
            assert "This should be level 1." in fixed_content
            assert "This should be level 2." in fixed_content

    def test_fix_headers_with_content(self):
        """Test that headers are added before existing content."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

Test project.
""")

            # Create a feature file with content but no headers
            feature_file = root / "feature_content.md"
            feature_file.write_text("""---
project: test
feature: content feature
linked_features: []
---

This is existing content in the file.

It has multiple paragraphs.

But no headers like Overview or Requirements.
""")

            # Load settings and run checks
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Apply fixes
            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Read fixed content
            fixed_content = feature_file.read_text()

            # Verify headers were added
            assert "# Overview" in fixed_content
            assert "## Requirements" in fixed_content

            # Verify existing content is preserved
            assert "This is existing content in the file." in fixed_content
            assert "It has multiple paragraphs." in fixed_content

            # Verify headers come before the existing content
            overview_pos = fixed_content.find("# Overview")
            content_pos = fixed_content.find("This is existing content")
            assert overview_pos < content_pos, "Headers should be inserted before existing content"

    def test_no_duplicate_headers(self):
        """Test that fixing headers with wrong levels doesn't create duplicates."""
        with tempfile.TemporaryDirectory() as tmpdir:
            root = Path(tmpdir)

            # Create a project file
            project_file = root / "project_test.md"
            project_file.write_text("""---
project: test
---

# Overview

Test project.
""")

            # Create a feature file with headers at wrong levels
            feature_file = root / "feature_no_dup.md"
            feature_file.write_text("""---
project: test
feature: no duplicates
linked_features: []
---

## Overview

Content under overview.

# Requirements

Content under requirements.
""")

            # Apply fixes
            settings = Settings()
            collector = Collector(settings, start_path=root)
            collected_data = collector.collect()
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            fixer = Fixer(settings)
            fixes_applied = fixer.fix_files(collected_data, diagnostics)

            # Read fixed content
            fixed_content = feature_file.read_text()

            # Count occurrences of each header
            overview_count = fixed_content.count("Overview")
            requirements_count = fixed_content.count("Requirements")

            # Should only have one of each header (no duplicates)
            assert overview_count == 1, f"Should have exactly 1 'Overview', found {overview_count}"
            assert requirements_count == 1, f"Should have exactly 1 'Requirements', found {requirements_count}"

            # Verify correct levels
            assert "# Overview" in fixed_content
            assert "## Requirements" in fixed_content


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
