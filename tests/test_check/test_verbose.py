"""Tests for the verbose mode functionality of the Check module."""

from pathlib import Path
from tempfile import TemporaryDirectory

from moff_cli.check import Checker
from moff_cli.collector import Collector
from moff_cli.settings import Settings


class TestVerboseMode:
    """Test cases for the verbose mode feature."""

    def test_verbose_mode_shows_expected_structure(self):
        """Test that verbose mode includes expected structure for files with errors."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a project file with errors
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Format with verbose mode
            verbose_lines = checker.format_diagnostics(
                diagnostics,
                root_directory=tmppath,
                verbose=True
            )

            # Convert to string for easier checking
            verbose_output = "\n".join(verbose_lines)

            # Check that expected structure is included
            assert "Expected structure for this file type (project):" in verbose_output
            assert "---" in verbose_output
            assert "project:" in verbose_output
            assert "# Overview" in verbose_output

    def test_non_verbose_mode_no_expected_structure(self):
        """Test that non-verbose mode doesn't show expected structure."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create a project file with errors
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Format without verbose mode
            normal_lines = checker.format_diagnostics(
                diagnostics,
                root_directory=tmppath,
                verbose=False
            )

            # Convert to string for easier checking
            normal_output = "\n".join(normal_lines)

            # Check that expected structure is NOT included
            assert "Expected structure for this file type" not in normal_output
            assert "# Overview" not in normal_output  # Only the header requirement

    def test_feature_file_expected_structure(self):
        """Test that feature files show correct expected structure in verbose mode."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            # Create feature directory and file with missing frontmatter
            features_dir = tmppath / "features"
            features_dir.mkdir()
            (features_dir / "feature_broken.md").write_text(
                "# Some Feature\n## Details"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Format with verbose mode
            verbose_lines = checker.format_diagnostics(
                diagnostics,
                root_directory=tmppath,
                verbose=True
            )

            # Convert to string for easier checking
            verbose_output = "\n".join(verbose_lines)

            # Check feature-specific expected structure
            assert "Expected structure for this file type (feature):" in verbose_output
            assert "project:" in verbose_output
            assert "feature:" in verbose_output
            assert "linked_features: []" in verbose_output
            assert "# Overview" in verbose_output
            assert "## Requirements" in verbose_output

    def test_tech_file_expected_structure(self):
        """Test that tech files show correct expected structure in verbose mode."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            # Create tech directory and file with errors
            tech_dir = tmppath / "tech"
            tech_dir.mkdir()
            (tech_dir / "tech_broken.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Format with verbose mode
            verbose_lines = checker.format_diagnostics(
                diagnostics,
                root_directory=tmppath,
                verbose=True
            )

            # Convert to string for easier checking
            verbose_output = "\n".join(verbose_lines)

            # Check tech-specific expected structure
            assert "Expected structure for this file type (tech):" in verbose_output
            assert "project:" in verbose_output
            assert "feature:" in verbose_output  # tech files have optional feature field
            assert "# Technical Details" in verbose_output
            assert "# Implementation Details" in verbose_output

    def test_save_with_verbose_mode(self):
        """Test that save_results includes expected structure when verbose=True."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file with errors
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Save with verbose mode
            results_path = checker.save_results(tmppath, diagnostics, verbose=True)

            # Read saved content
            content = results_path.read_text()

            # Check that expected structure is in saved file
            assert "Expected structure for this file type (project):" in content
            assert "---" in content
            assert "project:" in content
            assert "# Overview" in content

    def test_save_without_verbose_mode(self):
        """Test that save_results doesn't include expected structure when verbose=False."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file with errors
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Save without verbose mode
            results_path = checker.save_results(tmppath, diagnostics, verbose=False)

            # Read saved content
            content = results_path.read_text()

            # Check that expected structure is NOT in saved file
            assert "Expected structure for this file type" not in content

    def test_multiple_files_with_verbose(self):
        """Test verbose mode with multiple files having different errors."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file with header error
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Create feature directory
            features_dir = tmppath / "features"
            features_dir.mkdir()

            # Create feature file with missing frontmatter
            (features_dir / "feature_one.md").write_text(
                "# Some Feature\n## Details"
            )

            # Create another feature file with different errors
            (features_dir / "feature_two.md").write_text(
                "---\nproject: test\nfeature: two\n---\n# Wrong\n## Also Wrong"
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Format with verbose mode
            verbose_lines = checker.format_diagnostics(
                diagnostics,
                root_directory=tmppath,
                verbose=True
            )

            # Convert to string for easier checking
            verbose_output = "\n".join(verbose_lines)

            # Check that each file gets its own expected structure
            assert verbose_output.count("Expected structure for this file type") == 3
            assert verbose_output.count("(project):") == 1
            assert verbose_output.count("(feature):") == 2

    def test_no_errors_no_expected_structure(self):
        """Test that files without errors don't show expected structure even in verbose mode."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create valid project file
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview\n\nContent here."
            )

            # Create settings and checker
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Format with verbose mode
            verbose_lines = checker.format_diagnostics(
                diagnostics,
                root_directory=tmppath,
                verbose=True
            )

            # Convert to string for easier checking
            verbose_output = "\n".join(verbose_lines)

            # Check that no expected structure is shown when there are no errors
            assert "Expected structure for this file type" not in verbose_output
            assert "✓ All checks passed!" in verbose_output

    def test_generate_expected_structure_method(self):
        """Test the generate_expected_structure method directly."""
        settings = Settings()
        checker = Checker(settings)

        # Test project structure
        project_structure = checker.generate_expected_structure("project")
        project_lines = "\n".join(project_structure)
        assert "---" in project_lines
        assert "project:" in project_lines
        assert "# Overview" in project_lines

        # Test feature structure
        feature_structure = checker.generate_expected_structure("feature")
        feature_lines = "\n".join(feature_structure)
        assert "---" in feature_lines
        assert "project:" in feature_lines
        assert "feature:" in feature_lines
        assert "linked_features: []" in feature_lines
        assert "# Overview" in feature_lines
        assert "## Requirements" in feature_lines

        # Test tech structure
        tech_structure = checker.generate_expected_structure("tech")
        tech_lines = "\n".join(tech_structure)
        assert "---" in tech_lines
        assert "project:" in tech_lines
        assert "feature:" in tech_lines  # tech files have optional feature field
        assert "# Technical Details" in tech_lines
        assert "# Implementation Details" in tech_lines

    def test_cli_integration_with_verbose(self):
        """Test CLI integration with verbose flag."""
        import sys
        from argparse import Namespace
        from io import StringIO

        from moff_cli.cli import cmd_check

        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create project file with errors
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"
            )

            # Capture output for verbose mode
            verbose_output = StringIO()
            args_verbose = Namespace(
                save=False,
                path=tmppath,
                verbose=True
            )

            # Redirect stdout to capture output
            old_stdout = sys.stdout
            try:
                sys.stdout = verbose_output
                exit_code_verbose = cmd_check(args_verbose)
            finally:
                sys.stdout = old_stdout

            verbose_content = verbose_output.getvalue()

            # Capture output for normal mode
            normal_output = StringIO()
            args_normal = Namespace(
                save=False,
                path=tmppath,
                verbose=False
            )

            # Redirect stdout to capture output
            try:
                sys.stdout = normal_output
                exit_code_normal = cmd_check(args_normal)
            finally:
                sys.stdout = old_stdout

            normal_content = normal_output.getvalue()

            # Both should have non-zero exit codes due to errors
            assert exit_code_verbose != 0
            assert exit_code_normal != 0

            # Verbose output should contain expected structure
            assert "Expected structure for this file type" in verbose_content
            assert "---" in verbose_content  # Frontmatter delimiter
            assert "project:" in verbose_content  # Required field
            assert "# Overview" in verbose_content  # Required header

            # Normal output should NOT contain expected structure
            assert "Expected structure for this file type" not in normal_content

            # Verbose output should be longer than normal output
            assert len(verbose_content) > len(normal_content), \
                "Verbose mode should produce more output than normal mode"
