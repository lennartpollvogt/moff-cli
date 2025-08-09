"""Settings module for moff-cli.

This module handles configuration management for the moff documentation checker.
It loads settings from settings.json or uses defaults, and can create a default
settings.json file if none exists.
"""

import json
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any


class LocationConstraint(str, Enum):
    """Location constraints for markdown files."""
    ROOT_ONLY = "root_only"
    SUBDIRS_ONLY = "subdirs_only"
    ANY = "any"


class HeaderOrder(str, Enum):
    """Header order enforcement strategies."""
    STRICT = "strict"
    IN_ORDER = "in-order"
    ANY = "any"


class HeaderMatch(str, Enum):
    """Header text matching strategies."""
    EXACT = "exact"
    REGEX = "regex"


@dataclass
class HeaderRule:
    """Represents a header validation rule."""
    level: int
    text: str
    match: HeaderMatch = HeaderMatch.EXACT

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "level": self.level,
            "text": self.text,
            "match": self.match.value
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "HeaderRule":
        """Create from dictionary representation."""
        # Filter out comment keys (starting with _)
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        return cls(
            level=data["level"],
            text=data["text"],
            match=HeaderMatch(data.get("match", "exact"))
        )


@dataclass
class PrefixConfig:
    """Configuration for a markdown file prefix."""
    filename_pattern: str | None = None
    location: LocationConstraint = LocationConstraint.ANY
    frontmatter_required: dict[str, str] = field(default_factory=dict)
    frontmatter_optional: dict[str, str] = field(default_factory=dict)
    headers_required: list[HeaderRule] = field(default_factory=list)
    headers_optional: list[HeaderRule] = field(default_factory=list)
    headers_order: HeaderOrder = HeaderOrder.IN_ORDER

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        result = {
            "location": self.location.value,
            "frontmatter": {
                "required": self.frontmatter_required,
                "optional": self.frontmatter_optional
            },
            "headers": {
                "required": [h.to_dict() for h in self.headers_required],
                "optional": [h.to_dict() for h in self.headers_optional],
                "order": self.headers_order.value
            }
        }
        if self.filename_pattern:
            result["filename"] = {"pattern": self.filename_pattern}
        return result

    @classmethod
    def from_dict(cls, data: dict[str, Any], prefix_name: str) -> "PrefixConfig":
        """Create from dictionary representation."""
        # Filter out comment keys (starting with _)
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        filename_data = data.get("filename", {})
        pattern = filename_data.get("pattern")
        if pattern is None:
            pattern = f"{prefix_name}_*.md"

        frontmatter = data.get("frontmatter", {})
        # Filter comment keys from nested structures
        if isinstance(frontmatter.get("required"), dict):
            frontmatter["required"] = {k: v for k, v in frontmatter["required"].items() if not k.startswith("_")}
        if isinstance(frontmatter.get("optional"), dict):
            frontmatter["optional"] = {k: v for k, v in frontmatter.get("optional", {}).items() if not k.startswith("_")}

        headers = data.get("headers", {})
        # Filter comment keys from header lists
        if "required" in headers and isinstance(headers["required"], list):
            headers["required"] = [
                {k: v for k, v in h.items() if not k.startswith("_")}
                for h in headers["required"]
            ]
        if "optional" in headers and isinstance(headers["optional"], list):
            headers["optional"] = [
                {k: v for k, v in h.items() if not k.startswith("_")}
                for h in headers.get("optional", [])
            ]

        return cls(
            filename_pattern=pattern,
            location=LocationConstraint(data.get("location", "any")),
            frontmatter_required=frontmatter.get("required", {}),
            frontmatter_optional=frontmatter.get("optional", {}),
            headers_required=[
                HeaderRule.from_dict(h) for h in headers.get("required", [])
            ],
            headers_optional=[
                HeaderRule.from_dict(h) for h in headers.get("optional", [])
            ],
            headers_order=HeaderOrder(headers.get("order", "in-order"))
        )


@dataclass
class RootConfig:
    """Configuration for root directory detection."""
    detect_method: str = "project_file"
    detect_pattern: str = "project_*.md"
    override_path: str | None = None
    ignore_patterns: list[str] = field(default_factory=lambda: [
        "**/.git/**",
        "**/.venv/**",
        "**/node_modules/**"
    ])

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary representation."""
        return {
            "detect": {
                "method": self.detect_method,
                "pattern": self.detect_pattern
            },
            "override_path": self.override_path,
            "ignore": self.ignore_patterns
        }

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RootConfig":
        """Create from dictionary representation."""
        # Filter out comment keys (starting with _)
        data = {k: v for k, v in data.items() if not k.startswith("_")}

        detect = data.get("detect", {})
        # Filter comment keys from detect
        if isinstance(detect, dict):
            detect = {k: v for k, v in detect.items() if not k.startswith("_")}

        return cls(
            detect_method=detect.get("method", "project_file"),
            detect_pattern=detect.get("pattern", "project_*.md"),
            override_path=data.get("override_path"),
            ignore_patterns=data.get("ignore", [
                "**/.git/**",
                "**/.venv/**",
                "**/node_modules/**"
            ])
        )


class Settings:
    """Manages moff-cli configuration settings."""

    DEFAULT_VERSION = 1

    def __init__(self, settings_path: Path | None = None):
        """Initialize settings from file or defaults.

        Args:
            settings_path: Path to settings.json file. If None, uses defaults.
        """
        self.version = self.DEFAULT_VERSION
        self.root = RootConfig()
        self.prefixes: dict[str, PrefixConfig] = {}

        if settings_path and settings_path.exists():
            self._load_from_file(settings_path)
        else:
            self._load_defaults()

    def _load_defaults(self) -> None:
        """Load default settings."""
        # Project prefix configuration
        self.prefixes["project"] = PrefixConfig(
            filename_pattern="project_*.md",
            location=LocationConstraint.ROOT_ONLY,
            frontmatter_required={"project": "string"},
            frontmatter_optional={},
            headers_required=[
                HeaderRule(level=1, text="Overview", match=HeaderMatch.EXACT)
            ],
            headers_optional=[
                HeaderRule(level=2, text="Requirements", match=HeaderMatch.EXACT)
            ],
            headers_order=HeaderOrder.IN_ORDER
        )

        # Feature prefix configuration
        self.prefixes["feature"] = PrefixConfig(
            filename_pattern="feature_*.md",
            location=LocationConstraint.ANY,
            frontmatter_required={
                "project": "string",
                "feature": "string"
            },
            frontmatter_optional={"linked_features": "list"},
            headers_required=[
                HeaderRule(level=1, text="Overview", match=HeaderMatch.EXACT),
                HeaderRule(level=2, text="Requirements", match=HeaderMatch.EXACT)
            ],
            headers_optional=[],
            headers_order=HeaderOrder.STRICT
        )

        # Tech prefix configuration
        self.prefixes["tech"] = PrefixConfig(
            filename_pattern="tech_*.md",
            location=LocationConstraint.SUBDIRS_ONLY,
            frontmatter_required={"project": "string"},
            frontmatter_optional={
                "feature": "string",
                "linked_features": "list"
            },
            headers_required=[
                HeaderRule(level=1, text="Technical Details", match=HeaderMatch.EXACT),
                HeaderRule(level=1, text="Implementation Details", match=HeaderMatch.EXACT)
            ],
            headers_optional=[],
            headers_order=HeaderOrder.IN_ORDER
        )

    def _create_documented_defaults(self) -> dict[str, Any]:
        """Create default settings with documentation comments."""
        return {
            "_comment": "MOFF CLI Settings - Documentation validator configuration",
            "version": 1,
            "root": {
                "_comment": "Configure how MOFF discovers your documentation root directory",
                "detect": {
                    "_comment": "Method for finding documentation root. Currently only 'project_file' is supported",
                    "method": "project_file",
                    "pattern": "project_*.md",
                    "_pattern_help": "Glob pattern to identify the root marker file (e.g., 'project_*.md', 'main_*.md')"
                },
                "override_path": None,
                "_override_path_help": "Set to a specific path to bypass auto-detection (e.g., '/path/to/docs')",
                "ignore": [
                    "**/.git/**",
                    "**/.venv/**",
                    "**/node_modules/**"
                ],
                "_ignore_help": "Glob patterns for directories/files to exclude from scanning"
            },

            "prefixes": {
                "_comment": "Define validation rules for different file types based on their prefix",
                "_help": "Each prefix defines rules for files matching 'prefix_*.md' pattern",

                "project": {
                    "_comment": "Rules for project_*.md files - your main project documentation",
                    "location": "root_only",
                    "_location_values": "Options: 'root_only', 'subdirs_only', 'any'",
                    "_location_help": "Where these files must be located relative to documentation root",

                    "frontmatter": {
                        "_comment": "YAML frontmatter validation rules",
                        "required": {
                            "project": "string",
                            "_types": "Supported types: 'string', 'number', 'boolean', 'list', 'object'"
                        },
                        "optional": {
                            "_example": "Add optional fields like: {\"version\": \"string\", \"status\": \"string\"}"
                        }
                    },

                    "headers": {
                        "_comment": "Markdown header validation rules",
                        "required": [
                            {
                                "level": 1,
                                "text": "Overview",
                                "match": "exact",
                                "_match_values": "Options: 'exact' (must match exactly), 'regex' (text is treated as regex pattern)"
                            }
                        ],
                        "optional": [
                            {
                                "level": 2,
                                "text": "Requirements",
                                "match": "exact"
                            }
                        ],
                        "order": "in-order",
                        "_order_values": "Options: 'strict' (exact order), 'in-order' (correct order but gaps allowed), 'any' (no order enforced)"
                    },

                    "filename": {
                        "pattern": "project_*.md",
                        "_pattern_help": "Glob pattern for matching files of this type"
                    }
                },

                "feature": {
                    "_comment": "Rules for feature_*.md files - feature specifications",
                    "location": "any",
                    "frontmatter": {
                        "required": {
                            "project": "string",
                            "feature": "string"
                        },
                        "optional": {
                            "linked_features": "list",
                            "_list_example": "List values look like: ['feature1', 'feature2']"
                        }
                    },
                    "headers": {
                        "required": [
                            {"level": 1, "text": "Overview", "match": "exact"},
                            {"level": 2, "text": "Requirements", "match": "exact"}
                        ],
                        "optional": [],
                        "order": "strict"
                    },
                    "filename": {
                        "pattern": "feature_*.md"
                    }
                },

                "tech": {
                    "_comment": "Rules for tech_*.md files - technical implementation details",
                    "location": "subdirs_only",
                    "_location_note": "Tech files must be in subdirectories, not in root",
                    "frontmatter": {
                        "required": {
                            "project": "string"
                        },
                        "optional": {
                            "feature": "string",
                            "linked_features": "list"
                        }
                    },
                    "headers": {
                        "required": [
                            {"level": 1, "text": "Technical Details", "match": "exact"},
                            {"level": 1, "text": "Implementation Details", "match": "exact"}
                        ],
                        "optional": [],
                        "order": "in-order",
                        "_order_note": "Both level-1 headers must appear but can have other headers between them"
                    },
                    "filename": {
                        "pattern": "tech_*.md"
                    }
                },

                "_custom_prefix_example": {
                    "_comment": "Example: Add your own prefix type by copying this structure",
                    "_note": "Rename '_custom_prefix_example' to your prefix name (e.g., 'api', 'docs')",
                    "location": "any",
                    "frontmatter": {
                        "required": {"title": "string"},
                        "optional": {"tags": "list", "deprecated": "boolean"}
                    },
                    "headers": {
                        "required": [
                            {"level": 1, "text": ".*", "match": "regex"}
                        ],
                        "optional": [],
                        "order": "any"
                    },
                    "filename": {
                        "pattern": "custom_*.md"
                    }
                }
            }
        }

    def _load_from_file(self, settings_path: Path) -> None:
        """Load settings from JSON file.

        Args:
            settings_path: Path to settings.json file.
        """
        with open(settings_path) as f:
            data = json.load(f)

        self.version = data.get("version", self.DEFAULT_VERSION)

        # Load root configuration
        if "root" in data:
            self.root = RootConfig.from_dict(data["root"])
        else:
            self.root = RootConfig()

        # Load prefix configurations
        if "prefixes" in data:
            # Only load prefixes specified in the file (don't merge with defaults)
            for prefix_name, prefix_data in data["prefixes"].items():
                # Skip comment keys (starting with _)
                if not prefix_name.startswith("_"):
                    self.prefixes[prefix_name] = PrefixConfig.from_dict(
                        prefix_data, prefix_name
                    )
        else:
            # Use all defaults when no prefixes are specified
            self._load_defaults()

    def to_dict(self) -> dict[str, Any]:
        """Convert settings to dictionary representation."""
        return {
            "version": self.version,
            "root": self.root.to_dict(),
            "prefixes": {
                name: config.to_dict()
                for name, config in self.prefixes.items()
            }
        }

    def save_to_file(self, settings_path: Path) -> None:
        """Save settings to JSON file.

        Args:
            settings_path: Path where to save settings.json.
        """
        with open(settings_path, 'w') as f:
            json.dump(self.to_dict(), f, indent=2)

    @classmethod
    def create_default_settings_file(cls, root_dir: Path) -> Path:
        """Create a default settings.json file if it doesn't exist.

        Args:
            root_dir: Root directory where to create settings.json.

        Returns:
            Path to the settings file.
        """
        settings_path = root_dir / "settings.json"
        if not settings_path.exists():
            settings = cls()
            # Use the documented version for initial creation
            documented_settings = settings._create_documented_defaults()
            with open(settings_path, 'w') as f:
                json.dump(documented_settings, f, indent=2)
        return settings_path

    def get_prefix_config(self, prefix: str) -> PrefixConfig | None:
        """Get configuration for a specific prefix.

        Args:
            prefix: The prefix name (e.g., 'project', 'feature', 'tech').

        Returns:
            PrefixConfig if prefix exists, None otherwise.
        """
        return self.prefixes.get(prefix)

    def get_all_prefixes(self) -> list[str]:
        """Get list of all configured prefixes.

        Returns:
            List of prefix names.
        """
        return list(self.prefixes.keys())

    def validate_frontmatter_type(self, value: Any, expected_type: str) -> bool:
        """Validate that a value matches the expected type.

        Args:
            value: The value to validate.
            expected_type: Expected type ('string', 'number', 'boolean', 'list', 'object').

        Returns:
            True if type matches, False otherwise.
        """
        type_map = {
            "string": str,
            "number": (int, float),
            "boolean": bool,
            "list": list,
            "object": dict
        }

        if expected_type not in type_map:
            return False

        expected_python_type = type_map[expected_type]
        return isinstance(value, expected_python_type)
