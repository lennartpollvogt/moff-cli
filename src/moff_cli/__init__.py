"""MOFF CLI - Markdown Organization and Format Framework.

A command-line tool for validating and maintaining clean, organized documentation.
Designed to work seamlessly with LLMs in modern IDEs.
"""

from .__version__ import __version__
from .check import Checker, Diagnostic, RuleCategory, Severity
from .cli import main
from .collector import Collector
from .settings import (
    HeaderMatch,
    HeaderOrder,
    HeaderRule,
    LocationConstraint,
    PrefixConfig,
    RootConfig,
    Settings,
)
from .tree import TreeVisualizer, display_tree

__all__ = [
    # Version
    "__version__",

    # Settings module
    "Settings",
    "PrefixConfig",
    "RootConfig",
    "HeaderRule",
    "LocationConstraint",
    "HeaderOrder",
    "HeaderMatch",

    # Collector module
    "Collector",

    # Check module
    "Checker",
    "Diagnostic",
    "Severity",
    "RuleCategory",

    # Tree module
    "TreeVisualizer",
    "display_tree",

    # CLI
    "main",
]

# Package metadata
__author__ = "Lennart Pollvogt"
__email__ = "lennartpollvogt@protonmail.com"
__license__ = "MIT"
