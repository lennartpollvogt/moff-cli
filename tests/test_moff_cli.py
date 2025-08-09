"""Tests for moff-cli modules."""

from pathlib import Path
from tempfile import TemporaryDirectory

from moff_cli.check import Checker, Severity
from moff_cli.collector import Collector
from moff_cli.settings import Settings


class TestCollector:
    """Test cases for the Collector module."""

    def test_successful_collection(self):
        """Test successful collection of markdown files."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test structure
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview\nTest project"
            )

            feature_dir = tmppath / "features"
            feature_dir.mkdir()
            (feature_dir / "feature_auth.md").write_text(
                "---\nproject: test\nfeature: auth\n---\n# Overview\n## Requirements"
            )

            # Collect files
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            result = collector.collect()

            # Verify collection results
            assert result.get("error") is None
            assert result["root_directory"] == str(tmppath)
            assert "project" in result
            assert "feature" in result

            # Check project file found
            project_files = result["project"]
            assert len(project_files) == 1

            # Check feature file found
            feature_files = result["feature"]
            assert len(feature_files) == 1

    def test_no_root_file_error(self):
        """Test error when no root project file is found."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create directory without project file
            (tmppath / "feature_test.md").write_text(
                "---\nproject: test\nfeature: test\n---\n# Overview"
            )

            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            result = collector.collect()

            # Should have an error about missing root file
            assert result.get("error") is not None
            assert "No root file" in result["error"] or "not found" in result["error"]

    def test_ignore_patterns(self):
        """Test that ignore patterns work correctly (edge case)."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            # Create files that should be ignored
            venv_dir = tmppath / ".venv"
            venv_dir.mkdir()
            (venv_dir / "feature_ignored.md").write_text(
                "---\nproject: test\nfeature: ignored\n---\n# Overview"
            )

            git_dir = tmppath / ".git"
            git_dir.mkdir()
            (git_dir / "feature_git.md").write_text(
                "---\nproject: test\nfeature: git\n---\n# Overview"
            )

            # Create file that should be found
            (tmppath / "feature_valid.md").write_text(
                "---\nproject: test\nfeature: valid\n---\n# Overview"
            )

            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            result = collector.collect()

            # Verify ignored files are not collected
            feature_files = result.get("feature", {})

            assert "feature_valid.md" in str(list(feature_files.keys())[0])
            assert "feature_ignored.md" not in str(feature_files)
            assert "feature_git.md" not in str(feature_files)


class TestChecker:
    """Test cases for the Checker module."""

    def test_valid_documentation_passes(self):
        """Test that valid documentation passes all checks."""
        settings = Settings()
        checker = Checker(settings)

        # Create mock collected data with valid structure
        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": "/test/docs/project_test.md",
                "additional_root_candidates": []
            },
            "project": {
                "project_test.md": {
                    "is_in_root": True,
                    "md_list": [
                        {"metadata": {"project": "test"}, "start_line": 1},
                        {"header": {"level": 1, "content": "Overview"}, "start_line": 5}
                    ]
                }
            },
            "feature": {
                "features/feature_auth.md": {
                    "is_in_root": False,
                    "md_list": [
                        {
                            "metadata": {"project": "test", "feature": "auth"},
                            "start_line": 1
                        },
                        {"header": {"level": 1, "content": "Overview"}, "start_line": 5},
                        {"header": {"level": 2, "content": "Requirements"}, "start_line": 10}
                    ]
                }
            },
            "tech": {}
        }

        diagnostics = checker.check(collected_data)

        # Should have no diagnostics for valid documentation
        assert len(diagnostics) == 0
        assert checker.get_exit_code(diagnostics) == 0

    def test_location_constraint_violation(self):
        """Test detection of location constraint violations."""
        settings = Settings()
        checker = Checker(settings)

        # Tech files must be in subdirectories, but we'll put one in root
        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": "/test/docs/project_test.md",
                "additional_root_candidates": []
            },
            "project": {
                "project_test.md": {
                    "is_in_root": True,
                    "md_list": [
                        {"metadata": {"project": "test"}, "start_line": 1},
                        {"header": {"level": 1, "content": "Overview"}, "start_line": 5}
                    ]
                }
            },
            "feature": {},
            "tech": {
                "tech_impl.md": {
                    "is_in_root": True,  # This violates the subdirs_only constraint
                    "md_list": [
                        {"metadata": {"project": "test"}, "start_line": 1},
                        {"header": {"level": 1, "content": "Technical Details"}, "start_line": 5},
                        {"header": {"level": 1, "content": "Implementation Details"}, "start_line": 10}
                    ]
                }
            }
        }

        diagnostics = checker.check(collected_data)

        # Should have one location error
        assert len(diagnostics) == 1
        assert diagnostics[0].rule == "location.subdirs_only"
        assert diagnostics[0].severity == Severity.ERROR
        assert checker.get_exit_code(diagnostics) == 1

    def test_missing_required_header(self):
        """Test detection of missing required headers (edge case)."""
        settings = Settings()
        checker = Checker(settings)

        # Feature file missing the "Requirements" header
        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": "/test/docs/project_test.md",
                "additional_root_candidates": []
            },
            "project": {
                "project_test.md": {
                    "is_in_root": True,
                    "md_list": [
                        {"metadata": {"project": "test"}, "start_line": 1},
                        {"header": {"level": 1, "content": "Overview"}, "start_line": 5}
                    ]
                }
            },
            "feature": {
                "feature_incomplete.md": {
                    "is_in_root": False,
                    "md_list": [
                        {
                            "metadata": {"project": "test", "feature": "incomplete"},
                            "start_line": 1
                        },
                        {"header": {"level": 1, "content": "Overview"}, "start_line": 5}
                        # Missing the required "Requirements" header
                    ]
                }
            },
            "tech": {}
        }

        diagnostics = checker.check(collected_data)

        # Should have one header error
        assert len(diagnostics) == 1
        assert diagnostics[0].rule == "headers.missing"
        assert "Requirements" in diagnostics[0].message
        assert diagnostics[0].severity == Severity.ERROR



def test_integration_full_workflow():
    """Integration test: complete workflow from collection to checking."""
    with TemporaryDirectory() as tmpdir:
        tmppath = Path(tmpdir)

        # Create a mini documentation structure
        (tmppath / "project_app.md").write_text("""---
project: app
---

# Overview

This is the main application project.
""")

        features_dir = tmppath / "features"
        features_dir.mkdir()

        (features_dir / "feature_auth.md").write_text("""---
project: app
feature: auth
---

# Overview

Authentication feature.

## Requirements

- Users can log in
- Users can log out
""")

        # This tech file is intentionally in the wrong location (should be in subdir)
        (tmppath / "tech_database.md").write_text("""---
project: app
---

# Technical Details

Database implementation details.
""")

        # Run the full workflow
        settings = Settings()
        collector = Collector(settings, start_path=tmppath)
        collected_data = collector.collect()

        assert collected_data.get("error") is None

        checker = Checker(settings)
        diagnostics = checker.check(collected_data)

        # Should find at least two issues:
        # 1. tech file in wrong location
        # 2. tech file missing "Implementation Details" header
        assert len(diagnostics) >= 2

        location_errors = [d for d in diagnostics if "location" in d.rule]
        header_errors = [d for d in diagnostics if "headers" in d.rule]

        assert len(location_errors) >= 1
        assert len(header_errors) >= 1
