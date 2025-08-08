"""Tests for the Tree visualization feature."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from rich.console import Console
from rich.tree import Tree

from moff_cli.check import Checker, Diagnostic, Severity
from moff_cli.collector import Collector
from moff_cli.settings import Settings
from moff_cli.tree import TreeVisualizer


class TestTreeVisualizer:
    """Test cases for the TreeVisualizer class."""

    def test_basic_tree_visualization(self):
        """Test basic tree visualization without errors."""
        settings = Settings()
        console = MagicMock(spec=Console)
        visualizer = TreeVisualizer(settings, console)

        # Mock collected data
        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": "/test/docs/project_test.md",
                "additional_root_candidates": []
            },
            "project": {
                "docs/project_test.md": {
                    "is_in_root": True,
                    "md_list": []
                }
            },
            "feature": {
                "docs/features/feature_auth.md": {
                    "is_in_root": False,
                    "md_list": []
                },
                "docs/features/feature_users.md": {
                    "is_in_root": False,
                    "md_list": []
                }
            },
            "tech": {
                "docs/tech/tech_database.md": {
                    "is_in_root": False,
                    "md_list": []
                }
            }
        }

        # Show tree without diagnostics
        visualizer.show_tree(collected_data)

        # Verify console.print was called
        assert console.print.called
        # The tree should be printed at least once
        call_args = [call[0] for call in console.print.call_args_list]
        # Check that at least one Tree object was printed
        tree_printed = any(isinstance(arg[0], Tree) for arg in call_args if arg)
        assert tree_printed

    def test_tree_with_error_highlighting(self):
        """Test tree visualization with error highlighting."""
        settings = Settings()
        console = MagicMock(spec=Console)
        visualizer = TreeVisualizer(settings, console)

        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": "/test/docs/project_test.md",
                "additional_root_candidates": []
            },
            "project": {
                "docs/project_test.md": {
                    "is_in_root": True,
                    "md_list": []
                }
            },
            "feature": {
                "docs/features/feature_auth.md": {
                    "is_in_root": False,
                    "md_list": []
                },
                "docs/features/feature_broken.md": {
                    "is_in_root": False,
                    "md_list": []
                }
            },
            "tech": {}
        }

        # Create diagnostics with errors
        diagnostics = [
            Diagnostic(
                path="docs/features/feature_broken.md",
                prefix="feature",
                rule="headers.missing",
                message="Missing required header",
                severity=Severity.ERROR
            ),
            Diagnostic(
                path="docs/features/feature_auth.md",
                prefix="feature",
                rule="frontmatter.type",
                message="Type mismatch",
                severity=Severity.WARNING
            )
        ]

        visualizer.show_tree(collected_data, diagnostics=diagnostics)

        # Verify summary was shown
        assert console.print.called
        call_args = [str(call[0][0]) if call[0] else "" for call in console.print.call_args_list]

        # Check that summary information was printed
        summary_found = any("Files with errors:" in arg or "Total markdown files:" in arg for arg in call_args)
        assert summary_found or any("Summary" in arg for arg in call_args)

    def test_tree_errors_only_filter(self):
        """Test tree with errors-only filter."""
        settings = Settings()
        console = MagicMock(spec=Console)
        visualizer = TreeVisualizer(settings, console)

        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": "/test/docs/project_test.md",
                "additional_root_candidates": []
            },
            "project": {
                "docs/project_test.md": {
                    "is_in_root": True,
                    "md_list": []
                }
            },
            "feature": {
                "docs/features/feature_good.md": {
                    "is_in_root": False,
                    "md_list": []
                },
                "docs/features/feature_bad.md": {
                    "is_in_root": False,
                    "md_list": []
                }
            },
            "tech": {}
        }

        diagnostics = [
            Diagnostic(
                path="docs/features/feature_bad.md",
                prefix="feature",
                rule="headers.missing",
                message="Missing header",
                severity=Severity.ERROR
            )
        ]

        # Show only files with errors
        visualizer.show_tree(collected_data, diagnostics=diagnostics, show_only_errors=True)

        assert console.print.called

    def test_tree_with_collection_error(self):
        """Test tree visualization when collection has errors."""
        settings = Settings()
        console = MagicMock(spec=Console)
        visualizer = TreeVisualizer(settings, console)

        collected_data = {
            "error": "No root file matching pattern 'project_*.md' found",
            "root_directory": None
        }

        visualizer.show_tree(collected_data)

        # Should print error message
        console.print.assert_called()
        error_call = console.print.call_args_list[0]
        assert "No root file" in str(error_call[0][0])

    def test_get_file_icon(self):
        """Test file icon assignment based on prefix."""
        settings = Settings()
        visualizer = TreeVisualizer(settings)

        assert visualizer._get_file_icon("project_main.md") == "📋"
        assert visualizer._get_file_icon("feature_auth.md") == "⚡"
        assert visualizer._get_file_icon("tech_database.md") == "🔧"
        assert visualizer._get_file_icon("readme.md") == "📄"

    def test_directory_structure_building(self):
        """Test building directory structure from file paths."""
        settings = Settings()
        visualizer = TreeVisualizer(settings)

        file_paths = [
            "docs/project_main.md",
            "docs/features/feature_auth.md",
            "docs/features/feature_users.md",
            "docs/tech/impl/tech_database.md"
        ]

        structure = visualizer._build_directory_structure(file_paths)

        # Verify structure
        assert "docs" in structure
        assert "_files" in structure["docs"]
        assert "project_main.md" in structure["docs"]["_files"]
        assert "features" in structure["docs"]
        assert "_files" in structure["docs"]["features"]
        assert "feature_auth.md" in structure["docs"]["features"]["_files"]
        assert "tech" in structure["docs"]
        assert "impl" in structure["docs"]["tech"]
        assert "_files" in structure["docs"]["tech"]["impl"]

    def test_has_markdown_files(self):
        """Test checking if directory has markdown files."""
        settings = Settings()
        visualizer = TreeVisualizer(settings)

        # Structure with markdown files
        structure_with_md = {
            "_files": ["test.md", "readme.txt"],
            "subdir": {
                "_files": ["feature.md"]
            }
        }
        assert visualizer._has_markdown_files(structure_with_md) is True

        # Structure without markdown files
        structure_without_md = {
            "_files": ["readme.txt", "config.json"],
            "subdir": {
                "_files": ["script.py"]
            }
        }
        assert visualizer._has_markdown_files(structure_without_md) is False

        # Empty structure
        assert visualizer._has_markdown_files({}) is False

    def test_directory_has_issues(self):
        """Test checking if directory contains files with issues."""
        settings = Settings()
        visualizer = TreeVisualizer(settings)

        structure = {
            "_files": ["feature_auth.md"],
            "subdir": {
                "_files": ["tech_impl.md"]
            }
        }

        error_files = {"docs/feature_auth.md", "docs/other/error.md"}

        # Directory with issues
        assert visualizer._directory_has_issues("docs", structure, error_files) is True

        # Directory without issues
        assert visualizer._directory_has_issues("clean", structure, set()) is False

    def test_empty_documentation_tree(self):
        """Test tree visualization with no markdown files."""
        settings = Settings()
        console = MagicMock(spec=Console)
        visualizer = TreeVisualizer(settings, console)

        collected_data = {
            "root_directory": "/test/docs",
            "root": {
                "detection": {"method": "project_file", "pattern": "project_*.md"},
                "root_file": None,
                "additional_root_candidates": []
            },
            "project": {},
            "feature": {},
            "tech": {}
        }

        visualizer.show_tree(collected_data)
        assert console.print.called


class TestTreeIntegration:
    """Integration tests for tree visualization."""

    def test_tree_with_real_files(self):
        """Test tree visualization with real file system."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test structure
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview\nTest"
            )

            features_dir = tmppath / "features"
            features_dir.mkdir()
            (features_dir / "feature_auth.md").write_text(
                "---\nproject: test\nfeature: auth\n---\n# Overview\n## Requirements"
            )
            (features_dir / "feature_users.md").write_text(
                "---\nproject: test\nfeature: users\n---\n# Overview\n## Requirements"
            )

            tech_dir = tmppath / "tech"
            tech_dir.mkdir()
            (tech_dir / "tech_database.md").write_text(
                "---\nproject: test\n---\n# Technical Details\n# Implementation Details"
            )

            # Collect and visualize
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            # Check the data
            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Visualize
            console = MagicMock(spec=Console)
            visualizer = TreeVisualizer(settings, console)
            visualizer.show_tree(collected_data, diagnostics=diagnostics)

            # Verify tree was displayed
            assert console.print.called

    def test_display_tree_convenience_function(self):
        """Test the display_tree convenience function."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create minimal structure
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            # Test with mocked console to avoid actual output
            with patch('moff_cli.tree.tree.Console') as MockConsole:
                mock_console = MagicMock()
                MockConsole.return_value = mock_console

                from moff_cli.tree import display_tree

                # Test basic display
                display_tree(start_path=tmppath, show_errors=False)
                assert mock_console.print.called

                # Reset mock
                mock_console.reset_mock()

                # Test with errors
                display_tree(start_path=tmppath, show_errors=True)
                assert mock_console.print.called

                # Reset mock
                mock_console.reset_mock()

                # Test errors-only
                display_tree(start_path=tmppath, show_errors=True, show_only_errors=True)
                assert mock_console.print.called
