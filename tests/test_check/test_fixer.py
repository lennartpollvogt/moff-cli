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


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
