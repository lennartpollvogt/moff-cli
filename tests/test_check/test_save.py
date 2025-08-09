"""Tests for the Save feature of the Check module."""

from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import MagicMock, patch

from moff_cli.check import Checker, Diagnostic, Severity
from moff_cli.collector import Collector
from moff_cli.settings import Settings


class TestSaveFeature:
    """Test cases for the Save feature."""

    def test_save_results_format(self):
        """Test that save_results produces the correct format."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            settings = Settings()
            checker = Checker(settings)

            # Set the total files checked
            checker.total_files_checked = 5

            # Create diagnostics
            diagnostics = [
                Diagnostic(
                    path="collector/tech_collector.md",
                    prefix="tech",
                    rule="location.subdirs_only",
                    message="File is not allowed in root directory",
                    severity=Severity.ERROR
                ),
                Diagnostic(
                    path="tree/feature_tree.md",
                    prefix="feature",
                    rule="headers.missing",
                    message="Missing required header level=2 text='Requirements'",
                    severity=Severity.ERROR,
                    line=15
                )
            ]

            # Mock datetime to have consistent timestamp
            with patch('moff_cli.check.check.datetime') as mock_datetime:
                mock_datetime.now.return_value.strftime.return_value = "2024-01-15 14:30:22 UTC"

                results_path = checker.save_results(tmppath, diagnostics)

            # Verify file was created
            assert results_path.exists()
            assert results_path.name == "moff_results.txt"

            # Read and verify content
            content = results_path.read_text()

            # Check header
            assert "moff-cli check results" in content
            assert "Generated: 2024-01-15 14:30:22 UTC" in content
            assert f"Root: {tmppath}" in content

            # Check summary
            assert "Summary:" in content
            assert "Files checked: 5" in content
            assert "Total issues: 2" in content
            assert "Errors: 2" in content

            # Check violations format (grouped format)
            assert "Issues found:" in content
            assert "collector/tech_collector.md:" in content
            assert "  error  location.subdirs_only: File is not allowed in root directory" in content
            assert "tree/feature_tree.md:" in content
            assert "  error  headers.missing: Missing required header level=2 text='Requirements' (line 15)" in content

    def test_save_no_violations(self):
        """Test save_results when there are no violations."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            settings = Settings()
            checker = Checker(settings)
            checker.total_files_checked = 10

            # No diagnostics
            diagnostics = []

            results_path = checker.save_results(tmppath, diagnostics)

            content = results_path.read_text()

            # Check summary for no violations
            assert "Files checked: 10" in content
            assert "Total issues: 0" in content
            assert "✓ All checks passed!" in content
            assert "No validation issues found." in content

            # When there are no violations, the "Issues found:" section should not be present
            lines = content.split('\n')
            assert not any(line.strip() == "Issues found:" for line in lines)

    def test_save_mixed_severities(self):
        """Test save_results with mixed severity levels."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            settings = Settings()
            checker = Checker(settings)
            checker.total_files_checked = 3

            diagnostics = [
                Diagnostic(
                    path="file1.md",
                    prefix="feature",
                    rule="headers.missing",
                    message="Missing header",
                    severity=Severity.ERROR,
                    line=10
                ),
                Diagnostic(
                    path="file2.md",
                    prefix="tech",
                    rule="frontmatter.optional",
                    message="Optional field missing",
                    severity=Severity.WARNING,
                    line=1
                ),
                Diagnostic(
                    path="file3.md",
                    prefix="project",
                    rule="formatting.suggestion",
                    message="Consider reformatting",
                    severity=Severity.INFO,
                    line=5
                )
            ]

            results_path = checker.save_results(tmppath, diagnostics)
            content = results_path.read_text()

            # Check all severities are present in the grouped format
            assert "error" in content
            assert "warning" in content
            assert "info" in content

            # Check violations count
            assert "Total issues: 3" in content
            assert "Errors: 1" in content
            assert "Warnings: 1" in content
            assert "Info: 1" in content

    def test_save_deterministic_order(self):
        """Test that violations are saved in deterministic order."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            settings = Settings()
            checker = Checker(settings)
            checker.total_files_checked = 4

            # Create diagnostics in random order
            diagnostics = [
                Diagnostic(
                    path="b_file.md",
                    prefix="feature",
                    rule="z_rule",
                    message="Message B",
                    severity=Severity.ERROR,
                    line=20
                ),
                Diagnostic(
                    path="a_file.md",
                    prefix="tech",
                    rule="a_rule",
                    message="Message A",
                    severity=Severity.ERROR,
                    line=10
                ),
                Diagnostic(
                    path="b_file.md",
                    prefix="feature",
                    rule="a_rule",
                    message="Message B2",
                    severity=Severity.ERROR,
                    line=5
                ),
                Diagnostic(
                    path="a_file.md",
                    prefix="tech",
                    rule="b_rule",
                    message="Message A2",
                    severity=Severity.ERROR,
                    line=10
                )
            ]

            results_path = checker.save_results(tmppath, diagnostics)
            content = results_path.read_text()

            # Extract violation lines
            lines = content.split('\n')

            # Check grouped format: files are sorted, then diagnostics within each file are sorted by line, then rule
            # Files should appear in alphabetical order
            a_file_index = lines.index("a_file.md:")
            b_file_index = lines.index("b_file.md:")
            assert a_file_index < b_file_index

            # Check diagnostics order within each file
            # For a_file.md (both at line 10, sorted by rule)
            assert lines[a_file_index + 1].strip() == "error  a_rule: Message A (line 10)"
            assert lines[a_file_index + 2].strip() == "error  b_rule: Message A2 (line 10)"

            # For b_file.md (sorted by line number)
            assert lines[b_file_index + 1].strip() == "error  a_rule: Message B2 (line 5)"
            assert lines[b_file_index + 2].strip() == "error  z_rule: Message B (line 20)"

    def test_save_utf8_encoding(self):
        """Test that save_results uses UTF-8 encoding."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            settings = Settings()
            checker = Checker(settings)
            checker.total_files_checked = 1

            # Diagnostic with Unicode characters
            diagnostics = [
                Diagnostic(
                    path="file_émoji.md",
                    prefix="feature",
                    rule="headers.missing",
                    message="Missing header: 'Überblick' or '概要'",
                    severity=Severity.ERROR
                )
            ]

            results_path = checker.save_results(tmppath, diagnostics)

            # Should not raise encoding errors
            content = results_path.read_text(encoding='utf-8')
            assert "file_émoji.md" in content
            assert "Überblick" in content
            assert "概要" in content

    def test_save_overwrites_existing(self):
        """Test that save_results overwrites existing file."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)
            results_file = tmppath / "moff_results.txt"

            # Create existing file with old content
            results_file.write_text("Old results from previous run")

            settings = Settings()
            checker = Checker(settings)
            checker.total_files_checked = 2

            diagnostics = [
                Diagnostic(
                    path="new_file.md",
                    prefix="feature",
                    rule="new.rule",
                    message="New diagnostic",
                    severity=Severity.ERROR
                )
            ]

            results_path = checker.save_results(tmppath, diagnostics)
            content = results_path.read_text()

            # Old content should be gone
            assert "Old results" not in content
            # New content should be present
            assert "new_file.md" in content
            assert "New diagnostic" in content

    def test_file_count_accuracy(self):
        """Test that file count accurately reflects all checked files."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test files
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            features_dir = tmppath / "features"
            features_dir.mkdir()
            (features_dir / "feature_one.md").write_text(
                "---\nproject: test\nfeature: one\n---\n# Overview\n## Requirements"
            )
            (features_dir / "feature_two.md").write_text(
                "---\nproject: test\nfeature: two\n---\n# Overview\n## Requirements"
            )
            (features_dir / "feature_three.md").write_text(
                "---\nproject: test\nfeature: three\n---\n# Overview"  # Missing Requirements
            )

            # Run full workflow
            settings = Settings()
            collector = Collector(settings, start_path=tmppath)
            collected_data = collector.collect()

            checker = Checker(settings)
            diagnostics = checker.check(collected_data)

            # Save results
            results_path = checker.save_results(tmppath, diagnostics)
            content = results_path.read_text()

            # Should show 4 files checked (1 project + 3 features)
            assert "Files checked: 4" in content

            # Only feature_three should have a violation (in grouped format)
            assert "features/feature_three.md:" in content
            assert "features/feature_one.md:" not in content
            assert "features/feature_two.md:" not in content


class TestSaveIntegrationWithCLI:
    """Integration tests for Save feature with CLI."""

    def test_cli_save_flag_integration(self):
        """Test that --save flag properly triggers save functionality."""
        with TemporaryDirectory() as tmpdir:
            tmppath = Path(tmpdir)

            # Create test structure
            (tmppath / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            # Create a file with an error
            (tmppath / "tech_wrong.md").write_text(
                "---\nproject: test\n---\n# Wrong Header"  # Missing required headers
            )

            # Mock the CLI execution
            from argparse import Namespace

            from moff_cli.cli import cmd_check

            args = Namespace(
                save=True,
                path=tmppath,
                verbose=False
            )

            # Run check command with save
            with patch('moff_cli.cli.Console') as MockConsole:
                mock_console = MagicMock()
                MockConsole.return_value = mock_console

                exit_code = cmd_check(args)

                # Should have non-zero exit code due to errors
                assert exit_code != 0

                # Check that results file was created
                results_file = tmppath / "moff_results.txt"
                assert results_file.exists()

                # Verify content
                content = results_file.read_text()
                assert "moff-cli check results" in content
                assert "tech_wrong.md" in content

    def test_save_preserves_exit_code(self):
        """Test that saving doesn't affect exit code logic."""
        from argparse import Namespace

        from moff_cli.cli import cmd_check

        # Test with save=True and no errors
        with TemporaryDirectory() as tmpdir1:
            tmppath1 = Path(tmpdir1)

            # Create valid structure
            (tmppath1 / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            args_with_save = Namespace(save=True, path=tmppath1, verbose=False)

            with patch('moff_cli.cli.Console') as MockConsole:
                mock_console = MagicMock()
                MockConsole.return_value = mock_console

                exit_with_save = cmd_check(args_with_save)

                # Should have exit code 0 (success)
                assert exit_with_save == 0

                # Results file should be created when save=True
                results_file = tmppath1 / "moff_results.txt"
                assert results_file.exists(), "Results file should be created when save=True"

        # Test with save=False and no errors - use separate directory
        with TemporaryDirectory() as tmpdir2:
            tmppath2 = Path(tmpdir2)

            # Create valid structure
            (tmppath2 / "project_test.md").write_text(
                "---\nproject: test\n---\n# Overview"
            )

            args_without_save = Namespace(save=False, path=tmppath2, verbose=False)

            with patch('moff_cli.cli.Console') as MockConsole:
                mock_console = MagicMock()
                MockConsole.return_value = mock_console

                exit_without_save = cmd_check(args_without_save)

                # Should have same exit code (0 for success)
                assert exit_without_save == 0

                # Results file should NOT be created when save=False
                results_file = tmppath2 / "moff_results.txt"
                assert not results_file.exists(), "Results file should not be created when save=False"
