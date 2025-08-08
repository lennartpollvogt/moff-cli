"""MOFF CLI - Markdown Organization and Format Framework.

A command-line tool for validating and maintaining clean, organized documentation.
Designed to work seamlessly with LLMs in modern IDEs.
"""

from .__version__ import __version__
from .settings import (
    Settings,
    PrefixConfig,
    RootConfig,
    HeaderRule,
    LocationConstraint,
    HeaderOrder,
    HeaderMatch
)
from .collector import Collector
from .check import (
    Checker,
    Diagnostic,
    Severity,
    RuleCategory
)
from .tree import TreeVisualizer, display_tree
from .cli import main

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
