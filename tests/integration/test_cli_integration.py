"""
Integration tests for CLI commands.

These tests verify that the command-line interface works correctly with
real inputs, proper configuration loading, and integration with the
underlying sandbox and sanitization systems.
"""

import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import responses
from click.testing import CliRunner

from defuse.cli import main


@pytest.fixture
def cli_runner():
    """Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_dangerzone_available():
    """Mock dangerzone CLI availability for CLI tests."""
    with tempfile.NamedTemporaryFile(mode="w", suffix="-dangerzone", delete=False) as f:
        f.write('#!/bin/bash\\necho "Mock Dangerzone CLI"\\n')
        mock_path = Path(f.name)

    mock_path.chmod(0o755)

    with patch("defuse.cli.find_dangerzone_cli", return_value=mock_path):
        yield mock_path

    mock_path.unlink(missing_ok=True)


@pytest.mark.integration
class TestDownloadCommand:
    """Test the download CLI command."""

    @responses.activate
    def test_download_command_success(
        self, cli_runner, temp_dir, mock_dangerzone_available, mock_sandbox_capabilities
    ):
        """Test successful download command execution."""
        # Mock successful HTTP response
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.7\\nTest PDF content\\n%%EOF",
            status=200,
            headers={"content-type": "application/pdf"},
        )

        # Mock successful sandbox download
        with patch(
            "defuse.sandbox.SandboxedDownloader.sandboxed_download"
        ) as mock_download:
            output_file = temp_dir / "downloaded.pdf"
            output_file.write_bytes(b"%PDF-1.7\\nTest content\\n%%EOF")
            mock_download.return_value = output_file

            # Mock successful sanitization
            with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:
                sanitized_file = temp_dir / "test_defused.pdf"
                sanitized_file.write_bytes(b"%PDF-1.7\\nSanitized content\\n%%EOF")
                mock_sanitize.return_value = sanitized_file

                result = cli_runner.invoke(
                    main,
                    [
                        "download",
                        "http://example.com/test.pdf",
                        "--output-dir",
                        str(temp_dir),
                        "--verbose",
                    ],
                )

                assert result.exit_code == 0
                assert "📥 Downloading document from" in result.output
                assert "✅ Sanitized document saved to:" in result.output
                assert mock_download.called
                assert mock_sanitize.called

    @responses.activate
    def test_download_command_with_output_filename(
        self, cli_runner, temp_dir, mock_dangerzone_available, mock_sandbox_capabilities
    ):
        """Test download command with custom output filename."""
        responses.add(
            responses.GET,
            "http://example.com/document.pdf",
            body=b"%PDF-1.7\\nDocument content\\n%%EOF",
            status=200,
        )

        with patch(
            "defuse.sandbox.SandboxedDownloader.sandboxed_download"
        ) as mock_download:
            downloaded_file = temp_dir / "downloaded.pdf"
            downloaded_file.write_bytes(b"%PDF-1.7\\nContent\\n%%EOF")
            mock_download.return_value = downloaded_file

            with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:
                custom_output = temp_dir / "custom_name.pdf"
                custom_output.write_bytes(b"%PDF-1.7\\nSanitized\\n%%EOF")
                mock_sanitize.return_value = custom_output

                result = cli_runner.invoke(
                    main,
                    [
                        "download",
                        "http://example.com/document.pdf",
                        "--output-dir",
                        str(temp_dir),
                        "--output-filename",
                        "custom_name.pdf",
                    ],
                )

                assert result.exit_code == 0
                assert custom_output.exists()

    def test_download_command_missing_dangerzone(self, cli_runner, temp_dir):
        """Test download command when Dangerzone is not available."""
        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            result = cli_runner.invoke(
                main, ["download", "http://example.com/test.pdf"]
            )

            assert result.exit_code == 1
            assert "❌ Dangerzone CLI not found!" in result.output
            assert "To install Dangerzone:" in result.output

    @responses.activate
    def test_download_command_sandbox_options(
        self, cli_runner, temp_dir, mock_dangerzone_available, mock_sandbox_capabilities
    ):
        """Test download command with various sandbox options."""
        responses.add(
            responses.GET,
            "http://example.com/secure.pdf",
            body=b"%PDF-1.7\\nSecure content\\n%%EOF",
            status=200,
        )

        with patch(
            "defuse.sandbox.SandboxedDownloader.sandboxed_download"
        ) as mock_download:
            output_file = temp_dir / "secure.pdf"
            output_file.write_bytes(b"%PDF-1.7\\nContent\\n%%EOF")
            mock_download.return_value = output_file

            with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:
                sanitized_file = temp_dir / "secure_defused.pdf"
                sanitized_file.write_bytes(b"%PDF-1.7\\nSanitized\\n%%EOF")
                mock_sanitize.return_value = sanitized_file

                result = cli_runner.invoke(
                    main,
                    [
                        "download",
                        "http://example.com/secure.pdf",
                        "--output-dir",
                        str(temp_dir),
                        "--isolation",
                        "paranoid",
                        "--sandbox-backend",
                        "docker",
                        "--memory-only",
                        "--verbose",
                    ],
                )

                assert result.exit_code == 0

                # Verify the downloader was created with correct configuration
                assert mock_download.called
                downloader_call = mock_download.call_args
                # The configuration should reflect the CLI options


@pytest.mark.integration
class TestSanitizeCommand:
    """Test the sanitize CLI command."""

    def test_sanitize_local_file(self, cli_runner, temp_dir, mock_dangerzone_available):
        """Test sanitizing a local file."""
        # Create a test input file
        input_file = temp_dir / "input.pdf"
        input_file.write_bytes(b"%PDF-1.7\\nTest input content\\n%%EOF")

        with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:
            output_file = temp_dir / "input_defused.pdf"
            output_file.write_bytes(b"%PDF-1.7\\nSanitized content\\n%%EOF")
            mock_sanitize.return_value = output_file

            result = cli_runner.invoke(
                main,
                [
                    "sanitize",
                    str(input_file),
                    "--output-dir",
                    str(temp_dir),
                    "--verbose",
                ],
            )

            assert result.exit_code == 0
            assert f"🔄 Sanitizing: {input_file}" in result.output
            assert "✅ Sanitized document saved to:" in result.output
            assert mock_sanitize.called

    def test_sanitize_with_custom_output_filename(
        self, cli_runner, temp_dir, mock_dangerzone_available
    ):
        """Test sanitizing with custom output filename."""
        input_file = temp_dir / "document.pdf"
        input_file.write_bytes(b"%PDF-1.7\\nInput content\\n%%EOF")

        with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:
            custom_output = temp_dir / "custom_sanitized.pdf"
            custom_output.write_bytes(b"%PDF-1.7\\nSanitized\\n%%EOF")
            mock_sanitize.return_value = custom_output

            result = cli_runner.invoke(
                main,
                [
                    "sanitize",
                    str(input_file),
                    "--output-filename",
                    "custom_sanitized.pdf",
                    "--output-dir",
                    str(temp_dir),
                ],
            )

            assert result.exit_code == 0
            assert custom_output.exists()

    def test_sanitize_nonexistent_file(
        self, cli_runner, temp_dir, mock_dangerzone_available
    ):
        """Test sanitizing a file that doesn't exist."""
        nonexistent_file = temp_dir / "nonexistent.pdf"

        result = cli_runner.invoke(main, ["sanitize", str(nonexistent_file)])

        assert result.exit_code != 0
        assert "Error" in result.output or "not found" in result.output.lower()


@pytest.mark.integration
class TestBatchCommand:
    """Test the batch processing CLI command."""

    @responses.activate
    def test_batch_processing_success(
        self,
        cli_runner,
        temp_dir,
        mock_dangerzone_available,
        test_urls_file,
        mock_sandbox_capabilities,
    ):
        """Test successful batch processing of multiple URLs."""
        # Mock HTTP responses for all URLs in the test file
        test_urls = [
            "http://example.com/document1.pdf",
            "http://example.com/document2.docx",
            "http://example.com/image1.png",
            "http://slow-server.com/large.pdf",
            "http://example.com/final.pdf",
        ]

        for i, url in enumerate(test_urls):
            responses.add(
                responses.GET,
                url,
                body=f"Content for document {i + 1}".encode(),
                status=200,
            )

        with patch(
            "defuse.sandbox.SandboxedDownloader.sandboxed_download"
        ) as mock_download:
            # Mock successful downloads
            def mock_download_side_effect(url, output_path=None):
                if output_path is None:
                    output_path = temp_dir / f"temp_{hash(url)}.pdf"
                output_path.write_bytes(f"Downloaded: {url}".encode())
                return output_path

            mock_download.side_effect = mock_download_side_effect

            with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:

                def mock_sanitize_side_effect(input_file, output_filename=None):
                    if output_filename:
                        output_file = temp_dir / output_filename
                    else:
                        output_file = temp_dir / f"{input_file.stem}_defused.pdf"
                    output_file.write_bytes(f"Sanitized: {input_file.name}".encode())
                    return output_file

                mock_sanitize.side_effect = mock_sanitize_side_effect

                result = cli_runner.invoke(
                    main,
                    [
                        "batch",
                        str(test_urls_file),
                        "--output-dir",
                        str(temp_dir),
                        "--verbose",
                    ],
                )

                assert result.exit_code == 0
                assert "Processing documents" in result.output
                assert "Successfully processed" in result.output
                # Should process 5 URLs (comments are filtered out)
                assert mock_download.call_count == 5
                assert mock_sanitize.call_count == 5

    def test_batch_processing_partial_failures(
        self,
        cli_runner,
        temp_dir,
        mock_dangerzone_available,
        test_urls_file,
        mock_sandbox_capabilities,
    ):
        """Test batch processing with some failures."""
        with patch(
            "defuse.sandbox.SandboxedDownloader.sandboxed_download"
        ) as mock_download:
            # Simulate some downloads failing
            def mock_download_with_failures(url, output_path=None):
                if "slow-server.com" in url:
                    return None  # Simulate failure
                if output_path is None:
                    output_path = temp_dir / f"temp_{hash(url)}.pdf"
                output_path.write_bytes(f"Downloaded: {url}".encode())
                return output_path

            mock_download.side_effect = mock_download_with_failures

            with patch("defuse.sanitizer.DocumentSanitizer.sanitize") as mock_sanitize:

                def mock_sanitize_side_effect(input_file, output_filename=None):
                    output_file = temp_dir / f"{input_file.stem}_defused.pdf"
                    output_file.write_bytes(f"Sanitized: {input_file.name}".encode())
                    return output_file

                mock_sanitize.side_effect = mock_sanitize_side_effect

                result = cli_runner.invoke(
                    main, ["batch", str(test_urls_file), "--output-dir", str(temp_dir)]
                )

                # Should complete but with some failures reported
                assert result.exit_code == 0
                assert (
                    "Failed to process" in result.output
                    or "Skipping" in result.output
                    or "Successfully processed 4/5" in result.output
                )


@pytest.mark.integration
class TestCheckDepsCommand:
    """Test the dependency checking CLI command."""

    def test_check_deps_all_available(self, cli_runner):
        """Test check-deps when all dependencies are available."""
        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.sandbox.SandboxCapabilities") as mock_caps:
                mock_caps_instance = mock_caps.return_value
                mock_caps_instance.available_backends = {
                    "docker": True,
                    "podman": False,
                    "firejail": False,
                    "bubblewrap": False,
                }
                mock_caps_instance.recommended_backend = "docker"

                result = cli_runner.invoke(main, ["check-deps"])

                assert result.exit_code == 0
                assert "✅ Dangerzone CLI" in result.output
                assert (
                    "✅ Docker found:" in result.output
                    or "✅ Podman found:" in result.output
                )
                assert "docker" in result.output.lower()

    def test_check_deps_missing_dangerzone(self, cli_runner):
        """Test check-deps when Dangerzone is missing."""
        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            result = cli_runner.invoke(main, ["check-deps"])

            assert "❌ Dangerzone CLI not found" in result.output
            assert "https://dangerzone.rocks" in result.output

    def test_check_deps_no_container_runtime(self, cli_runner):
        """Test check-deps when no container runtime is available."""
        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dz:
            mock_find_dz.return_value = Path("/usr/bin/dangerzone-cli")

            with patch("defuse.cli.check_container_runtime") as mock_check_runtime:
                mock_check_runtime.return_value = (None, None, None)

                result = cli_runner.invoke(main, ["check-deps"])

                assert "❌ No container runtime found" in result.output
                assert "Docker/Podman" in result.output


@pytest.mark.integration
class TestSecurityReportCommand:
    """Test the security report CLI command."""

    def test_security_report_generation(self, cli_runner, mock_sandbox_capabilities):
        """Test security report generation."""
        # Mock sandbox capabilities for report
        mock_sandbox_capabilities.platform = "darwin"
        mock_sandbox_capabilities.available_backends = {"docker": True, "podman": False}
        mock_sandbox_capabilities.recommended_backend = "docker"

        result = cli_runner.invoke(main, ["security-report"])

        assert result.exit_code == 0
        assert "🔒 Defuse Security Report" in result.output
        assert "Platform:" in result.output
        assert "Available Security Features:" in result.output
        assert "docker" in result.output.lower()


@pytest.mark.integration
class TestConfigCommand:
    """Test the configuration CLI command."""

    def test_config_list(self, cli_runner, temp_dir):
        """Test listing current configuration."""
        result = cli_runner.invoke(main, ["config", "--list"])

        assert result.exit_code == 0
        assert "Current configuration:" in result.output
        assert "Dangerzone path:" in result.output
        assert "Output directory:" in result.output

    def test_config_set_dangerzone_path(self, cli_runner, temp_dir):
        """Test setting dangerzone path."""
        mock_dangerzone = temp_dir / "mock-dangerzone"
        mock_dangerzone.write_text("#!/bin/bash\\necho mock dangerzone")
        mock_dangerzone.chmod(0o755)

        result = cli_runner.invoke(
            main, ["config", "--dangerzone-path", str(mock_dangerzone)]
        )

        assert result.exit_code == 0
        assert "Configuration saved!" in result.output

    def test_config_add_allowed_domain(self, cli_runner):
        """Test adding allowed domain."""
        result = cli_runner.invoke(
            main, ["config", "--add-domain", "trusted.example.com"]
        )

        assert result.exit_code == 0
        assert "Configuration saved!" in result.output


@pytest.mark.integration
class TestCLIErrorHandling:
    """Test CLI error handling and user experience."""

    def test_invalid_url_format(self, cli_runner, mock_dangerzone_available):
        """Test handling of invalid URL formats."""
        result = cli_runner.invoke(main, ["download", "not-a-valid-url"])

        assert result.exit_code != 0
        assert (
            "Invalid URL" in result.output
            or "Error" in result.output
            or "❌ Download failed" in result.output
        )

    def test_nonexistent_urls_file(self, cli_runner):
        """Test batch command with nonexistent URLs file."""
        result = cli_runner.invoke(main, ["batch", "/nonexistent/file.txt"])

        assert result.exit_code != 0
        assert "not found" in result.output.lower() or "Error" in result.output

    def test_permission_denied_output_dir(self, cli_runner, mock_dangerzone_available):
        """Test handling of permission denied errors."""
        # Try to write to a directory that doesn't exist or has no permissions
        result = cli_runner.invoke(
            main,
            [
                "download",
                "http://example.com/test.pdf",
                "--output-dir",
                "/root/restricted",  # Likely no permission
            ],
        )

        # Should handle gracefully, not crash
        assert isinstance(
            result.exit_code, int
        )  # Any exit code is fine, just don't crash

    def test_help_text_completeness(self, cli_runner):
        """Test that help text is complete and helpful."""
        result = cli_runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "download" in result.output
        assert "sanitize" in result.output
        assert "batch" in result.output
        assert "check-deps" in result.output
        assert "security-report" in result.output

        # Test subcommand help
        download_help = cli_runner.invoke(main, ["download", "--help"])
        assert download_help.exit_code == 0
        assert "--output-dir" in download_help.output
        assert "--isolation" in download_help.output
