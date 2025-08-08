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
        filename_data = data.get("filename", {})
        pattern = filename_data.get("pattern")
        if pattern is None:
            pattern = f"{prefix_name}_*.md"

        frontmatter = data.get("frontmatter", {})
        headers = data.get("headers", {})

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
        detect = data.get("detect", {})
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
            # Start with defaults
            self._load_defaults()
            # Override with file settings
            for prefix_name, prefix_data in data["prefixes"].items():
                if prefix_name in self.prefixes:
                    # Merge with existing defaults
                    self.prefixes[prefix_name] = PrefixConfig.from_dict(
                        prefix_data, prefix_name
                    )
                else:
                    # New prefix
                    self.prefixes[prefix_name] = PrefixConfig.from_dict(
                        prefix_data, prefix_name
                    )
        else:
            # Use all defaults
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
            settings.save_to_file(settings_path)
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
