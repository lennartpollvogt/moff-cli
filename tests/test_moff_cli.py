"""Tests for moff-cli modules."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from moff_cli.check import Checker, Severity
from moff_cli.collector import Collector
from moff_cli.settings import LocationConstraint, Settings


class TestSettings:
    """Test cases for the Settings module."""

    def test_default_settings_loaded(self):
        """Test that default settings are properly loaded."""
        settings = Settings()

        # Check version
        assert settings.version == 1

        # Check root configuration
        assert settings.root.detect_method == "project_file"
        assert settings.root.detect_pattern == "project_*.md"

        # Check prefixes are configured
        prefixes = settings.get_all_prefixes()
        assert "project" in prefixes
        assert "feature" in prefixes
        assert "tech" in prefixes

        # Check project prefix configuration
        project_config = settings.get_prefix_config("project")
        assert project_config is not None
        assert project_config.location == LocationConstraint.ROOT_ONLY
        assert "project" in project_config.frontmatter_required

    def test_settings_from_file(self):
        """Test loading settings from a JSON file."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create custom settings
            custom_settings = {
                "version": 1,
                "root": {
                    "detect": {
                        "method": "project_file",
                        "pattern": "custom_*.md"
                    },
                    "ignore": ["**/test/**"]
                },
                "prefixes": {
                    "custom": {
                        "location": "any",
                        "frontmatter": {
                            "required": {"name": "string"},
                            "optional": {}
                        },
                        "headers": {
                            "required": [],
                            "optional": [],
                            "order": "any"
                        }
                    }
                }
            }

            # Write settings file
            with open(settings_path, 'w') as f:
                json.dump(custom_settings, f)

            # Load settings
            settings = Settings(settings_path)

            # Verify custom settings loaded
            assert settings.root.detect_pattern == "custom_*.md"
            assert "**/test/**" in settings.root.ignore_patterns
            assert "custom" in settings.get_all_prefixes()

            custom_config = settings.get_prefix_config("custom")
            assert custom_config is not None
            assert custom_config.location == LocationConstraint.ANY

    def test_type_validation(self):
        """Test frontmatter type validation (edge case with various types)."""
        settings = Settings()

        # Test valid types
        assert settings.validate_frontmatter_type("text", "string") is True
        assert settings.validate_frontmatter_type(42, "number") is True
        assert settings.validate_frontmatter_type(3.14, "number") is True
        assert settings.validate_frontmatter_type(True, "boolean") is True
        assert settings.validate_frontmatter_type([], "list") is True
        assert settings.validate_frontmatter_type({}, "object") is True

        # Test invalid types
        assert settings.validate_frontmatter_type(123, "string") is False
        assert settings.validate_frontmatter_type("text", "number") is False
        assert settings.validate_frontmatter_type("true", "boolean") is False
        assert settings.validate_frontmatter_type({}, "list") is False
        assert settings.validate_frontmatter_type([], "object") is False

        # Test edge case: unknown type
        assert settings.validate_frontmatter_type("anything", "unknown_type") is False


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

    def test_settings_auto_creation(self):
        """Test that settings.json is automatically created when it doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file but no settings.json
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview\nTest project"
            )

            # Verify settings.json doesn't exist initially
            settings_path = tmppath / "settings.json"
            assert not settings_path.exists()

            # Create and save default settings
            Settings.create_default_settings_file(tmppath)

            # Verify settings.json was created
            assert settings_path.exists()

            # Load and verify the created settings
            with open(settings_path) as f:
                saved_settings = json.load(f)

            assert saved_settings["version"] == 1
            assert "root" in saved_settings
            assert "prefixes" in saved_settings
            assert "project" in saved_settings["prefixes"]
            assert "feature" in saved_settings["prefixes"]
            assert "tech" in saved_settings["prefixes"]


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
