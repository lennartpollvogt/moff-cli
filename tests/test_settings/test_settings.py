"""Tests for the Settings module."""

import json
from pathlib import Path
from tempfile import TemporaryDirectory

from moff_cli.settings import (
    HeaderMatch,
    HeaderOrder,
    HeaderRule,
    LocationConstraint,
    PrefixConfig,
    RootConfig,
    Settings,
)


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

    def test_settings_completely_replace_defaults(self):
        """Test that custom settings completely replace defaults (not merge)."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create custom settings with only one prefix
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

            # Verify ONLY custom prefix exists (defaults should be gone)
            prefixes = settings.get_all_prefixes()
            assert len(prefixes) == 1
            assert "custom" in prefixes
            assert "project" not in prefixes
            assert "feature" not in prefixes
            assert "tech" not in prefixes

            custom_config = settings.get_prefix_config("custom")
            assert custom_config is not None
            assert custom_config.location == LocationConstraint.ANY

    def test_settings_from_file_with_multiple_custom_prefixes(self):
        """Test loading settings with multiple custom prefixes."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create custom settings with api and docs prefixes
            custom_settings = {
                "version": 1,
                "root": {
                    "detect": {
                        "method": "project_file",
                        "pattern": "project_*.md"
                    }
                },
                "prefixes": {
                    "api": {
                        "location": "subdirs_only",
                        "frontmatter": {
                            "required": {
                                "endpoint": "string",
                                "method": "string"
                            },
                            "optional": {"deprecated": "boolean"}
                        },
                        "headers": {
                            "required": [
                                {"level": 1, "text": "Endpoint", "match": "exact"},
                                {"level": 2, "text": "Request", "match": "exact"}
                            ],
                            "optional": [],
                            "order": "strict"
                        }
                    },
                    "docs": {
                        "location": "any",
                        "frontmatter": {
                            "required": {"title": "string"},
                            "optional": {}
                        },
                        "headers": {
                            "required": [
                                {"level": 1, "text": ".*", "match": "regex"}
                            ],
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

            # Verify only custom prefixes exist
            prefixes = settings.get_all_prefixes()
            assert len(prefixes) == 2
            assert "api" in prefixes
            assert "docs" in prefixes
            assert "project" not in prefixes
            assert "feature" not in prefixes
            assert "tech" not in prefixes

            # Verify api prefix configuration
            api_config = settings.get_prefix_config("api")
            assert api_config is not None
            assert api_config.location == LocationConstraint.SUBDIRS_ONLY
            assert "endpoint" in api_config.frontmatter_required
            assert "method" in api_config.frontmatter_required
            assert "deprecated" in api_config.frontmatter_optional

            # Verify docs prefix configuration
            docs_config = settings.get_prefix_config("docs")
            assert docs_config is not None
            assert docs_config.location == LocationConstraint.ANY
            assert "title" in docs_config.frontmatter_required
            assert len(docs_config.headers_required) == 1
            assert docs_config.headers_required[0].match == HeaderMatch.REGEX

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

    def test_settings_ignore_comment_keys(self):
        """Test that comment keys (starting with _) are ignored when loading."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create settings with comment keys
            settings_with_comments = {
                "_comment": "This is a comment that should be ignored",
                "version": 1,
                "root": {
                    "_comment": "Root configuration comment",
                    "detect": {
                        "_comment": "Detection method comment",
                        "method": "project_file",
                        "pattern": "project_*.md",
                        "_pattern_help": "This explains the pattern"
                    },
                    "override_path": None,
                    "_override_path_help": "This explains override_path",
                    "ignore": ["**/.git/**"]
                },
                "prefixes": {
                    "_comment": "Prefixes comment",
                    "_help": "General help text",
                    "project": {
                        "_comment": "Project prefix comment",
                        "location": "root_only",
                        "_location_help": "Location help text",
                        "frontmatter": {
                            "_comment": "Frontmatter comment",
                            "required": {
                                "project": "string",
                                "_types": "Type information"
                            },
                            "optional": {
                                "_example": "Example text"
                            }
                        },
                        "headers": {
                            "_comment": "Headers comment",
                            "required": [
                                {
                                    "level": 1,
                                    "text": "Overview",
                                    "match": "exact",
                                    "_match_values": "Match value options"
                                }
                            ],
                            "optional": [],
                            "order": "strict",
                            "_order_values": "Order options"
                        },
                        "filename": {
                            "pattern": "project_*.md",
                            "_pattern_help": "Pattern help"
                        }
                    },
                    "_custom_prefix_example": {
                        "_comment": "This entire section should be ignored",
                        "location": "any",
                        "frontmatter": {
                            "required": {"title": "string"}
                        }
                    }
                }
            }

            # Write settings file with comments
            with open(settings_path, 'w') as f:
                json.dump(settings_with_comments, f, indent=2)

            # Load settings
            settings = Settings(settings_path)

            # Verify comments are ignored and settings loaded correctly
            assert settings.version == 1
            assert settings.root.detect_pattern == "project_*.md"

            # Verify only real prefixes are loaded (not _custom_prefix_example)
            prefixes = settings.get_all_prefixes()
            assert len(prefixes) == 1
            assert "project" in prefixes
            assert "_custom_prefix_example" not in prefixes
            assert "_comment" not in prefixes

            # Verify project config loaded correctly without comment interference
            project_config = settings.get_prefix_config("project")
            assert project_config is not None
            assert project_config.location == LocationConstraint.ROOT_ONLY
            assert "project" in project_config.frontmatter_required
            assert "_types" not in project_config.frontmatter_required
            assert "_example" not in project_config.frontmatter_optional


class TestPrefixConfig:
    """Test cases for PrefixConfig class."""

    def test_prefix_config_from_dict_with_defaults(self):
        """Test creating PrefixConfig from dict with missing values using defaults."""
        data = {
            "location": "any",
            "frontmatter": {
                "required": {"title": "string"}
            }
        }

        config = PrefixConfig.from_dict(data, "test")

        assert config.filename_pattern == "test_*.md"  # Should use prefix name as default
        assert config.location == LocationConstraint.ANY
        assert config.frontmatter_required == {"title": "string"}
        assert config.frontmatter_optional == {}
        assert config.headers_required == []
        assert config.headers_optional == []
        assert config.headers_order == HeaderOrder.IN_ORDER

    def test_prefix_config_to_dict_round_trip(self):
        """Test converting PrefixConfig to dict and back."""
        original = PrefixConfig(
            filename_pattern="api_*.md",
            location=LocationConstraint.SUBDIRS_ONLY,
            frontmatter_required={"endpoint": "string", "method": "string"},
            frontmatter_optional={"deprecated": "boolean"},
            headers_required=[
                HeaderRule(level=1, text="Endpoint", match=HeaderMatch.EXACT),
                HeaderRule(level=2, text="Request", match=HeaderMatch.EXACT)
            ],
            headers_optional=[
                HeaderRule(level=3, text="Examples", match=HeaderMatch.EXACT)
            ],
            headers_order=HeaderOrder.STRICT
        )

        # Convert to dict
        data = original.to_dict()

        # Convert back to PrefixConfig
        restored = PrefixConfig.from_dict(data, "api")

        # Verify all fields match
        assert restored.filename_pattern == original.filename_pattern
        assert restored.location == original.location
        assert restored.frontmatter_required == original.frontmatter_required
        assert restored.frontmatter_optional == original.frontmatter_optional
        assert len(restored.headers_required) == len(original.headers_required)
        assert len(restored.headers_optional) == len(original.headers_optional)
        assert restored.headers_order == original.headers_order

        # Verify header rules match
        for orig_header, restored_header in zip(original.headers_required, restored.headers_required, strict=False):
            assert orig_header.level == restored_header.level
            assert orig_header.text == restored_header.text
            assert orig_header.match == restored_header.match


class TestRootConfig:
    """Test cases for RootConfig class."""

    def test_root_config_defaults(self):
        """Test RootConfig default values."""
        config = RootConfig()

        assert config.detect_method == "project_file"
        assert config.detect_pattern == "project_*.md"
        assert config.override_path is None
        assert "**/.git/**" in config.ignore_patterns
        assert "**/.venv/**" in config.ignore_patterns
        assert "**/node_modules/**" in config.ignore_patterns

    def test_root_config_from_dict(self):
        """Test creating RootConfig from dict."""
        data = {
            "detect": {
                "method": "project_file",
                "pattern": "main_*.md"
            },
            "override_path": "/custom/path",
            "ignore": ["**/build/**", "**/dist/**"]
        }

        config = RootConfig.from_dict(data)

        assert config.detect_method == "project_file"
        assert config.detect_pattern == "main_*.md"
        assert config.override_path == "/custom/path"
        assert config.ignore_patterns == ["**/build/**", "**/dist/**"]

    def test_root_config_to_dict_round_trip(self):
        """Test converting RootConfig to dict and back."""
        original = RootConfig(
            detect_method="project_file",
            detect_pattern="main_*.md",
            override_path="/custom/path",
            ignore_patterns=["**/build/**", "**/dist/**", "**/cache/**"]
        )

        # Convert to dict
        data = original.to_dict()

        # Convert back to RootConfig
        restored = RootConfig.from_dict(data)

        # Verify all fields match
        assert restored.detect_method == original.detect_method
        assert restored.detect_pattern == original.detect_pattern
        assert restored.override_path == original.override_path
        assert restored.ignore_patterns == original.ignore_patterns


class TestHeaderRule:
    """Test cases for HeaderRule class."""

    def test_header_rule_defaults(self):
        """Test HeaderRule default values."""
        rule = HeaderRule(level=1, text="Overview")

        assert rule.level == 1
        assert rule.text == "Overview"
        assert rule.match == HeaderMatch.EXACT

    def test_header_rule_from_dict(self):
        """Test creating HeaderRule from dict."""
        data = {
            "level": 2,
            "text": "Requirements.*",
            "match": "regex"
        }

        rule = HeaderRule.from_dict(data)

        assert rule.level == 2
        assert rule.text == "Requirements.*"
        assert rule.match == HeaderMatch.REGEX

    def test_header_rule_to_dict_round_trip(self):
        """Test converting HeaderRule to dict and back."""
        original = HeaderRule(
            level=3,
            text="Implementation",
            match=HeaderMatch.EXACT
        )

        # Convert to dict
        data = original.to_dict()

        # Convert back to HeaderRule
        restored = HeaderRule.from_dict(data)

        # Verify all fields match
        assert restored.level == original.level
        assert restored.text == original.text
        assert restored.match == original.match


class TestSettingsIntegration:
    """Integration tests for Settings functionality."""

    def test_settings_auto_creation(self):
        """Test that settings.json is automatically created when it doesn't exist."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

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

    def test_empty_prefixes_uses_defaults(self):
        """Test that when no prefixes are specified in file, defaults are used."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create settings with only root config (no prefixes)
            custom_settings = {
                "version": 1,
                "root": {
                    "detect": {
                        "method": "project_file",
                        "pattern": "project_*.md"
                    }
                }
            }

            # Write settings file without prefixes
            with open(settings_path, 'w') as f:
                json.dump(custom_settings, f)

            # Load settings
            settings = Settings(settings_path)

            # Should use default prefixes when none specified
            prefixes = settings.get_all_prefixes()
            assert "project" in prefixes
            assert "feature" in prefixes
            assert "tech" in prefixes

    def test_settings_save_and_load_consistency(self):
        """Test that saving and loading settings maintains consistency."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create original settings
            original = Settings()
            original.root.detect_pattern = "main_*.md"
            original.root.ignore_patterns.append("**/custom/**")

            # Add a custom prefix
            original.prefixes["custom"] = PrefixConfig(
                filename_pattern="custom_*.md",
                location=LocationConstraint.ANY,
                frontmatter_required={"name": "string"},
                headers_required=[HeaderRule(level=1, text="Title", match=HeaderMatch.EXACT)]
            )

            # Save settings
            original.save_to_file(settings_path)

            # Load settings from file
            loaded = Settings(settings_path)

            # Verify loaded settings match original
            assert loaded.version == original.version
            assert loaded.root.detect_pattern == original.root.detect_pattern
            assert "**/custom/**" in loaded.root.ignore_patterns

            # Verify custom prefix loaded correctly
            custom_config = loaded.get_prefix_config("custom")
            assert custom_config is not None
            assert custom_config.filename_pattern == "custom_*.md"
            assert custom_config.location == LocationConstraint.ANY
            assert "name" in custom_config.frontmatter_required
            assert len(custom_config.headers_required) == 1
            assert custom_config.headers_required[0].text == "Title"

    def test_documented_defaults_creation(self):
        """Test that documented default settings are created with proper comments."""
        with TemporaryDirectory() as tmpdir:
            settings_path = Path(tmpdir) / "settings.json"

            # Create default settings file
            Settings.create_default_settings_file(Path(tmpdir))

            # Verify file was created
            assert settings_path.exists()

            # Read the raw JSON to check for comments
            with open(settings_path) as f:
                raw_settings = json.load(f)

            # Verify comments exist in the file
            assert "_comment" in raw_settings
            assert "MOFF CLI Settings" in raw_settings["_comment"]

            # Verify root comments
            assert "_comment" in raw_settings["root"]
            assert "_override_path_help" in raw_settings["root"]
            assert "_ignore_help" in raw_settings["root"]

            # Verify prefix comments
            assert "_comment" in raw_settings["prefixes"]
            assert "_help" in raw_settings["prefixes"]

            # Verify project prefix has comments
            if "project" in raw_settings["prefixes"]:
                project = raw_settings["prefixes"]["project"]
                assert "_comment" in project
                assert "_location_values" in project
                assert "_location_help" in project

            # Verify custom prefix example exists
            assert "_custom_prefix_example" in raw_settings["prefixes"]

            # Now verify the settings still load correctly
            loaded_settings = Settings(settings_path)
            assert loaded_settings.version == 1

            # Verify default prefixes are loaded (not the example)
            prefixes = loaded_settings.get_all_prefixes()
            assert "project" in prefixes
            assert "feature" in prefixes
            assert "tech" in prefixes
            assert "_custom_prefix_example" not in prefixes
