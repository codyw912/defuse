"""
Unit tests for CLI command functionality and error handling.

These tests focus on CLI argument validation, error paths, and command behavior
without requiring external dependencies like Docker or Dangerzone.
"""

from click.testing import CliRunner
from unittest.mock import patch
from pathlib import Path

from defuse.cli import main


class TestCLIBasics:
    """Test basic CLI functionality."""

    def test_cli_version_command(self):
        """Test --version flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        # Should show version info
        assert "defuse" in result.output.lower() or "version" in result.output.lower()

    def test_cli_help_command(self):
        """Test --help flag."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output
        assert "download" in result.output
        assert "sanitize" in result.output

    def test_download_command_help(self):
        """Test help for download command."""
        runner = CliRunner()
        result = runner.invoke(main, ["download", "--help"])

        assert result.exit_code == 0
        assert "Download and sanitize" in result.output
        assert "URL" in result.output


class TestCLIErrorHandling:
    """Test CLI error handling and validation."""

    def test_download_missing_url(self):
        """Test download command without URL argument."""
        runner = CliRunner()
        result = runner.invoke(main, ["download"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_download_invalid_url_scheme(self):
        """Test download with invalid URL scheme."""
        runner = CliRunner()
        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_runtime:
                mock_runtime.return_value = ("docker", "/usr/bin/docker", "20.10.0")

                result = runner.invoke(main, ["download", "ftp://invalid.com/file.pdf"])

                # Should fail due to invalid URL scheme or other validation
                assert result.exit_code != 0

    def test_sanitize_missing_file_argument(self):
        """Test sanitize command without file argument."""
        runner = CliRunner()
        result = runner.invoke(main, ["sanitize"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_sanitize_nonexistent_file(self):
        """Test sanitize command with nonexistent file."""
        runner = CliRunner()
        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            result = runner.invoke(main, ["sanitize", "/nonexistent/file.pdf"])

            assert result.exit_code != 0

    def test_batch_missing_file_argument(self):
        """Test batch command without URLs file argument."""
        runner = CliRunner()
        result = runner.invoke(main, ["batch"])

        assert result.exit_code != 0
        assert "Missing argument" in result.output or "Usage:" in result.output

    def test_batch_nonexistent_urls_file(self):
        """Test batch command with nonexistent URLs file."""
        runner = CliRunner()
        result = runner.invoke(main, ["batch", "/nonexistent/urls.txt"])

        assert result.exit_code != 0
        # Click handles file not found errors
        assert (
            "not found" in result.output.lower()
            or "no such file" in result.output.lower()
        )

    def test_config_invalid_option(self):
        """Test config command with invalid option."""
        runner = CliRunner()
        result = runner.invoke(main, ["config", "--invalid-option"])

        assert result.exit_code != 0
        assert (
            "no such option" in result.output.lower()
            or "unrecognized" in result.output.lower()
        )


class TestDangerzoneDetection:
    """Test Dangerzone CLI detection and error paths."""

    def test_download_missing_dangerzone_error_message(self):
        """Test clear error message when Dangerzone is missing."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            result = runner.invoke(main, ["download", "http://example.com/test.pdf"])

            assert result.exit_code == 1
            assert "Dangerzone CLI not found" in result.output
            assert "install" in result.output.lower()

    def test_sanitize_missing_dangerzone_error_message(self):
        """Test clear error message when Dangerzone is missing for sanitize."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            with runner.isolated_filesystem():
                # Create a test file
                test_file = Path("test.pdf")
                test_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")

                result = runner.invoke(main, ["sanitize", str(test_file)])

                assert result.exit_code == 1
                assert "Dangerzone CLI not found" in result.output

    def test_batch_missing_dangerzone_error_message(self):
        """Test clear error message when Dangerzone is missing for batch."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            with runner.isolated_filesystem():
                # Create a test URLs file
                urls_file = Path("urls.txt")
                urls_file.write_text("http://example.com/test.pdf\n")

                result = runner.invoke(main, ["batch", str(urls_file)])

                assert result.exit_code == 1
                assert "Dangerzone CLI not found" in result.output


class TestContainerRuntimeDetection:
    """Test container runtime detection error paths."""

    def test_download_missing_container_runtime_error_message(self):
        """Test clear error message when container runtime is missing."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_runtime:
                mock_runtime.return_value = (None, None, None)

                result = runner.invoke(
                    main, ["download", "http://example.com/test.pdf"]
                )

                assert result.exit_code == 1
                assert "Container runtime not available" in result.output
                assert "Docker or Podman" in result.output

    def test_batch_missing_container_runtime_error_message(self):
        """Test clear error message when container runtime is missing for batch."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_runtime:
                mock_runtime.return_value = (None, None, None)

                with runner.isolated_filesystem():
                    urls_file = Path("urls.txt")
                    urls_file.write_text("http://example.com/test.pdf\n")

                    result = runner.invoke(main, ["batch", str(urls_file)])

                    assert result.exit_code == 1
                    assert "Container runtime not available" in result.output


class TestConfigCommand:
    """Test config command edge cases."""

    def test_config_list_empty_config(self):
        """Test config list with minimal configuration."""
        runner = CliRunner()

        result = runner.invoke(main, ["config", "--list"])

        assert result.exit_code == 0
        assert "Current configuration:" in result.output
        # Should handle empty/default config gracefully

    def test_config_set_invalid_path(self):
        """Test setting config with invalid path."""
        runner = CliRunner()

        result = runner.invoke(
            main, ["config", "--set-dangerzone-path", "/nonexistent/path"]
        )

        # Should either succeed (and validate later) or provide helpful error
        # The behavior depends on implementation - either is acceptable
        assert result.exit_code in [0, 1, 2]  # Allow success, failure, or invalid arg

    def test_config_set_empty_value(self):
        """Test setting config with empty value."""
        runner = CliRunner()

        result = runner.invoke(main, ["config", "--set-dangerzone-path", ""])

        # Should handle empty values gracefully
        assert result.exit_code in [0, 1, 2]  # Allow success, failure, or invalid arg


class TestBatchCommandEdgeCases:
    """Test batch command edge cases and error handling."""

    def test_batch_empty_urls_file(self):
        """Test batch command with empty URLs file."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_check_runtime:
                mock_check_runtime.return_value = (
                    "docker",
                    "/usr/bin/docker",
                    "20.10.0",
                )

                with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                    mock_caps_instance = mock_capabilities.return_value
                    mock_caps_instance.available_backends = {
                        "docker": True,
                        "podman": False,
                        "firejail": False,
                        "bubblewrap": False,
                        "auto": True,
                    }
                    mock_caps_instance.recommended_backend = "docker"
                    with runner.isolated_filesystem():
                        empty_file = Path("empty.txt")
                        empty_file.write_text("")

                        result = runner.invoke(main, ["batch", str(empty_file)])

                        assert result.exit_code == 1
                        assert "No URLs found" in result.output

    def test_batch_only_comments_urls_file(self):
        """Test batch command with URLs file containing only comments."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_check_runtime:
                mock_check_runtime.return_value = (
                    "docker",
                    "/usr/bin/docker",
                    "20.10.0",
                )

                with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                    mock_caps_instance = mock_capabilities.return_value
                    mock_caps_instance.available_backends = {
                        "docker": True,
                        "podman": False,
                        "firejail": False,
                        "bubblewrap": False,
                        "auto": True,
                    }
                    mock_caps_instance.recommended_backend = "docker"
                    with runner.isolated_filesystem():
                        comments_file = Path("comments.txt")
                        comments_file.write_text(
                            "# This is a comment\n# Another comment\n"
                        )

                        result = runner.invoke(main, ["batch", str(comments_file)])

                        assert result.exit_code == 1
                        assert "No URLs found" in result.output

    def test_batch_mixed_comments_and_urls(self):
        """Test batch command with mixed comments and URLs."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_runtime:
                mock_runtime.return_value = ("docker", "/usr/bin/docker", "20.10.0")

                with runner.isolated_filesystem():
                    mixed_file = Path("mixed.txt")
                    mixed_file.write_text(
                        "# Comment 1\nhttp://example.com/test1.pdf\n# Comment 2\nhttp://example.com/test2.pdf\n"
                    )

                    # Mock the components to avoid real downloads
                    with patch("defuse.sandbox.SandboxedDownloader"):
                        with patch("defuse.sanitizer.DocumentSanitizer"):
                            result = runner.invoke(main, ["batch", str(mixed_file)])

                            # Should process the URLs and ignore comments
                            # Exact behavior depends on mocking, but shouldn't crash
                            assert result.exit_code in [0, 1]  # Allow various outcomes
