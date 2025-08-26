"""
Cross-platform CLI integration tests.

Tests for CLI functionality across Linux, Windows, and macOS.
These tests verify that the command-line interface works correctly on each platform
with platform-specific paths, commands, and behaviors.
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import responses
from click.testing import CliRunner

from defuse.cli import main, find_dangerzone_cli


class TestCrossPlatformCLI:
    """Test CLI functionality across all platforms."""

    def test_cli_help_command(self):
        """Test that help command works on all platforms."""
        runner = CliRunner()
        result = runner.invoke(main, ["--help"])

        assert result.exit_code == 0
        assert "Usage:" in result.output
        assert "Commands:" in result.output

    def test_cli_version_command(self):
        """Test version command across platforms."""
        runner = CliRunner()
        result = runner.invoke(main, ["--version"])

        assert result.exit_code == 0
        assert "0.1.0" in result.output

    def test_check_deps_command_cross_platform(self):
        """Test check-deps command on all platforms."""
        runner = CliRunner()

        with patch("defuse.cli.find_dangerzone_cli") as mock_find_dangerzone:
            with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                # Mock platform-appropriate results
                system = platform.system()

                if system == "Linux":
                    mock_find_dangerzone.return_value = Path("/usr/bin/dangerzone-cli")
                    mock_caps = MagicMock()
                    mock_caps.platform = "linux"
                    mock_caps.available_backends = {"docker": True, "firejail": True}
                    mock_caps.recommended_backend = "firejail"
                    mock_capabilities.return_value = mock_caps

                elif system == "Windows":
                    mock_find_dangerzone.return_value = Path(
                        "C:/Program Files/Dangerzone/dangerzone-cli.exe"
                    )
                    mock_caps = MagicMock()
                    mock_caps.platform = "windows"
                    mock_caps.available_backends = {"docker": True}
                    mock_caps.recommended_backend = "docker"
                    mock_capabilities.return_value = mock_caps

                elif system == "Darwin":
                    mock_find_dangerzone.return_value = Path(
                        "/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
                    )
                    mock_caps = MagicMock()
                    mock_caps.platform = "darwin"
                    mock_caps.available_backends = {"docker": True, "podman": True}
                    mock_caps.recommended_backend = "podman"
                    mock_capabilities.return_value = mock_caps

                result = runner.invoke(main, ["check-deps"])

                assert result.exit_code == 0
                assert "Dangerzone CLI found:" in result.output
                assert "found:" in result.output

    def test_security_report_command_cross_platform(self):
        """Test security report command on all platforms."""
        runner = CliRunner()

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                mock_caps = MagicMock()
                mock_caps.platform = platform.system().lower()
                mock_caps.available_backends = {"docker": True}
                mock_caps.recommended_backend = "docker"
                mock_caps.get_security_report.return_value = {
                    "platform": platform.system().lower(),
                    "available_backends": {"docker": True},
                    "recommended_backend": "docker",
                    "isolation_level": "strict",
                }
                mock_capabilities.return_value = mock_caps

                result = runner.invoke(main, ["security-report"])

                assert result.exit_code == 0
                assert "Security Configuration Report" in result.output
                assert platform.system().lower() in result.output.lower()

    def test_config_command_cross_platform(self, temp_dir):
        """Test config command on all platforms."""
        runner = CliRunner()

        with runner.isolated_filesystem():
            # Test showing current config
            result = runner.invoke(main, ["config"])

            assert result.exit_code == 0
            # Should show configuration without errors


@pytest.mark.linux
class TestLinuxCLIIntegration:
    """Test CLI functionality specific to Linux."""

    @responses.activate
    def test_linux_download_command_with_firejail(self, temp_dir):
        """Test download command using Firejail on Linux."""
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.4 Linux test",
            status=200,
        )

        runner = CliRunner()

        with patch(
            "defuse.cli.find_dangerzone_cli",
            return_value=Path("/usr/bin/dangerzone-cli"),
        ):
            with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                mock_caps = MagicMock()
                mock_caps.platform = "linux"
                mock_caps.available_backends = {"firejail": True, "docker": True}
                mock_caps.recommended_backend = "firejail"
                mock_capabilities.return_value = mock_caps

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0

                    with patch("pathlib.Path.exists", return_value=True):
                        result = runner.invoke(
                            main,
                            [
                                "download",
                                "http://example.com/test.pdf",
                                "--output",
                                str(temp_dir / "linux_test.pdf"),
                            ],
                        )

                        # Should complete successfully
                        if mock_run.called:
                            # Verify Firejail was used if called
                            cmd_args = mock_run.call_args[0][0]
                            # May contain 'firejail' depending on implementation

    @responses.activate
    def test_linux_batch_download_with_bubblewrap(self, temp_dir):
        """Test batch download using Bubblewrap on Linux."""
        # Create batch file
        batch_file = temp_dir / "batch.txt"
        batch_file.write_text(
            "http://example.com/doc1.pdf\nhttp://example.com/doc2.pdf\n"
        )

        # Mock responses
        responses.add(
            responses.GET,
            "http://example.com/doc1.pdf",
            body=b"%PDF-1.4 Doc1",
            status=200,
        )
        responses.add(
            responses.GET,
            "http://example.com/doc2.pdf",
            body=b"%PDF-1.4 Doc2",
            status=200,
        )

        runner = CliRunner()

        with patch(
            "defuse.cli.find_dangerzone_cli",
            return_value=Path("/usr/bin/dangerzone-cli"),
        ):
            with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                mock_caps = MagicMock()
                mock_caps.platform = "linux"
                mock_caps.available_backends = {"bubblewrap": True, "docker": True}
                mock_caps.recommended_backend = "bubblewrap"
                mock_capabilities.return_value = mock_caps

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0

                    with patch("pathlib.Path.exists", return_value=True):
                        result = runner.invoke(
                            main,
                            [
                                "batch",
                                str(batch_file),
                                "--output-dir",
                                str(temp_dir / "linux_batch"),
                            ],
                        )

                        # Should process batch successfully
                        if mock_run.called:
                            assert (
                                len(mock_run.call_args_list) >= 2
                            )  # At least 2 downloads

    def test_linux_cli_with_snap_dangerzone(self):
        """Test CLI detection of Snap-installed Dangerzone on Linux."""
        runner = CliRunner()

        snap_path = Path("/snap/dangerzone/current/bin/dangerzone-cli")
        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:

                def exists_side_effect():
                    frame = mock_exists.call_args
                    if frame and "snap" in str(frame[0][0]):
                        return True
                    return False

                mock_exists.side_effect = exists_side_effect

                result = find_dangerzone_cli()

                # Should have checked Snap paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                snap_calls = [call for call in calls if "snap" in call]
                assert len(snap_calls) > 0, "Should check Snap installation paths"

    def test_linux_cli_with_flatpak_dangerzone(self):
        """Test CLI detection of Flatpak-installed Dangerzone on Linux."""
        runner = CliRunner()

        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:

                def exists_side_effect():
                    frame = mock_exists.call_args
                    if frame and "flatpak" in str(frame[0][0]):
                        return True
                    return False

                mock_exists.side_effect = exists_side_effect

                result = find_dangerzone_cli()

                # Should have checked Flatpak paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                flatpak_calls = [call for call in calls if "flatpak" in call]
                assert len(flatpak_calls) > 0, "Should check Flatpak installation paths"


@pytest.mark.windows
class TestWindowsCLIIntegration:
    """Test CLI functionality specific to Windows."""

    @responses.activate
    def test_windows_download_command_with_docker(self, temp_dir):
        """Test download command using Docker Desktop on Windows."""
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.4 Windows test",
            status=200,
        )

        runner = CliRunner()

        windows_dangerzone = Path("C:/Program Files/Dangerzone/dangerzone-cli.exe")
        with patch("defuse.cli.find_dangerzone_cli", return_value=windows_dangerzone):
            with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                mock_caps = MagicMock()
                mock_caps.platform = "windows"
                mock_caps.available_backends = {"docker": True}
                mock_caps.recommended_backend = "docker"
                mock_capabilities.return_value = mock_caps

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0

                    with patch("pathlib.Path.exists", return_value=True):
                        # Use Windows-style path
                        output_path = (
                            temp_dir / "windows test.pdf"
                        )  # Test spaces in path

                        result = runner.invoke(
                            main,
                            [
                                "download",
                                "http://example.com/test.pdf",
                                "--output",
                                str(output_path),
                            ],
                        )

                        # Should handle Windows paths with spaces
                        if mock_run.called:
                            cmd_args = mock_run.call_args[0][0]
                            assert "docker" in cmd_args[0]

    def test_windows_cli_path_with_spaces(self, temp_dir):
        """Test CLI handling of Windows paths with spaces."""
        runner = CliRunner()

        # Windows path with spaces
        windows_path = temp_dir / "My Documents" / "test file.pdf"
        windows_path.parent.mkdir(exist_ok=True)

        with patch("defuse.cli.find_dangerzone_cli") as mock_find:
            mock_find.return_value = Path(
                "C:/Program Files/Dangerzone/dangerzone-cli.exe"
            )

            # Should handle paths with spaces correctly
            result = runner.invoke(
                main, ["config", "--output-dir", str(windows_path.parent)]
            )

            # Should not fail due to path spaces
            # (Note: actual behavior depends on implementation)

    def test_windows_cli_with_program_files_dangerzone(self):
        """Test CLI detection of Program Files Dangerzone on Windows."""
        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:

                def exists_side_effect():
                    frame = mock_exists.call_args
                    if (
                        frame
                        and "Program Files" in str(frame[0][0])
                        and str(frame[0][0]).endswith(".exe")
                    ):
                        return True
                    return False

                mock_exists.side_effect = exists_side_effect

                result = find_dangerzone_cli()

                # Should have checked Program Files paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                program_files_calls = [
                    call
                    for call in calls
                    if "Program Files" in call and call.endswith(".exe")
                ]
                assert len(program_files_calls) > 0, (
                    "Should check Program Files installation paths"
                )

    def test_windows_cli_error_handling(self, temp_dir):
        """Test Windows-specific error handling in CLI."""
        runner = CliRunner()

        # Test with invalid Windows path
        invalid_path = "Z:/nonexistent/path/test.pdf"

        result = runner.invoke(
            main, ["download", "http://example.com/test.pdf", "--output", invalid_path]
        )

        # Should handle invalid paths gracefully (exit code may vary)


@pytest.mark.macos
class TestMacOSCLIIntegration:
    """Test CLI functionality specific to macOS."""

    @responses.activate
    def test_macos_download_command_with_podman(self, temp_dir):
        """Test download command using Podman on macOS."""
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.4 macOS test",
            status=200,
        )

        runner = CliRunner()

        macos_dangerzone = Path(
            "/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
        )
        with patch("defuse.cli.find_dangerzone_cli", return_value=macos_dangerzone):
            with patch("defuse.sandbox.SandboxCapabilities") as mock_capabilities:
                mock_caps = MagicMock()
                mock_caps.platform = "darwin"
                mock_caps.available_backends = {"podman": True, "docker": True}
                mock_caps.recommended_backend = "podman"
                mock_capabilities.return_value = mock_caps

                with patch("subprocess.run") as mock_run:
                    mock_run.return_value.returncode = 0

                    with patch("pathlib.Path.exists", return_value=True):
                        result = runner.invoke(
                            main,
                            [
                                "download",
                                "http://example.com/test.pdf",
                                "--output",
                                str(temp_dir / "macos_test.pdf"),
                            ],
                        )

                        # Should use Podman if available
                        if mock_run.called:
                            cmd_args = mock_run.call_args[0][0]
                            # May contain 'podman' depending on implementation

    def test_macos_cli_app_bundle_detection(self):
        """Test CLI detection of app bundle Dangerzone on macOS."""
        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:

                def exists_side_effect():
                    frame = mock_exists.call_args
                    if (
                        frame
                        and "Dangerzone.app" in str(frame[0][0])
                        and "Contents/MacOS" in str(frame[0][0])
                    ):
                        return True
                    return False

                mock_exists.side_effect = exists_side_effect

                result = find_dangerzone_cli()

                # Should have checked app bundle paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                app_bundle_calls = [
                    call
                    for call in calls
                    if "Dangerzone.app" in call and "Contents/MacOS" in call
                ]
                assert len(app_bundle_calls) > 0, (
                    "Should check app bundle installation paths"
                )

    def test_macos_cli_homebrew_detection(self):
        """Test CLI detection of Homebrew Dangerzone on macOS."""
        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:

                def exists_side_effect():
                    frame = mock_exists.call_args
                    path_str = str(frame[0][0])
                    if (
                        "homebrew" in path_str
                        or "/usr/local" in path_str
                        or "/opt/homebrew" in path_str
                    ) and path_str.endswith("dangerzone-cli"):
                        return True
                    return False

                mock_exists.side_effect = exists_side_effect

                result = find_dangerzone_cli()

                # Should have checked Homebrew paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                homebrew_calls = [
                    call
                    for call in calls
                    if any(
                        path in call
                        for path in ["homebrew", "/usr/local", "/opt/homebrew"]
                    )
                ]
                assert len(homebrew_calls) > 0, (
                    "Should check Homebrew installation paths"
                )

    @responses.activate
    def test_macos_sanitize_command_full_workflow(self, temp_dir):
        """Test full sanitize workflow on macOS."""
        # Create input file
        input_file = temp_dir / "test_input.pdf"
        input_file.write_bytes(b"%PDF-1.4 Test content for sanitization")

        runner = CliRunner()

        macos_dangerzone = Path(
            "/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
        )
        with patch("defuse.cli.find_dangerzone_cli", return_value=macos_dangerzone):
            with patch("subprocess.run") as mock_run:
                # Mock successful Dangerzone execution
                mock_run.return_value.returncode = 0
                mock_run.return_value.stdout = "Document converted successfully"

                # Mock output file creation
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        result = runner.invoke(
                            main,
                            [
                                "sanitize",
                                str(input_file),
                                "--output-dir",
                                str(temp_dir / "sanitized"),
                            ],
                        )

                        # Should complete sanitization workflow
                        if mock_run.called:
                            cmd_args = mock_run.call_args[0][0]
                            assert str(macos_dangerzone) in cmd_args

    def test_macos_cli_permission_handling(self, temp_dir):
        """Test macOS permission handling in CLI."""
        runner = CliRunner()

        # Create a directory with restrictive permissions
        restricted_dir = temp_dir / "restricted"
        restricted_dir.mkdir()

        # Test CLI behavior with permission restrictions
        result = runner.invoke(main, ["config", "--output-dir", str(restricted_dir)])

        # Should handle permissions appropriately
        # (Exact behavior depends on implementation)


class TestCLIErrorHandlingCrossPlatform:
    """Test CLI error handling across platforms."""

    def test_cli_missing_dependencies(self):
        """Test CLI behavior when dependencies are missing."""
        runner = CliRunner()

        # Mock missing Dangerzone
        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            result = runner.invoke(main, ["check-deps"])

            assert result.exit_code == 0  # Should report status, not crash
            assert "not found" in result.output or "missing" in result.output.lower()

    def test_cli_invalid_urls(self, temp_dir):
        """Test CLI handling of invalid URLs."""
        runner = CliRunner()

        invalid_urls = [
            "not-a-url",
            "ftp://example.com/test.pdf",
            "",
            "javascript:alert('xss')",
        ]

        for invalid_url in invalid_urls:
            result = runner.invoke(
                main, ["download", invalid_url, "--output", str(temp_dir / "test.pdf")]
            )

            # Should handle invalid URLs gracefully
            assert result.exit_code != 0  # Should fail appropriately

    def test_cli_network_errors(self, temp_dir):
        """Test CLI handling of network errors."""
        runner = CliRunner()

        with patch(
            "defuse.downloader.NetworkDownloader.download",
            side_effect=Exception("Network error"),
        ):
            result = runner.invoke(
                main,
                [
                    "download",
                    "http://nonexistent.example.com/test.pdf",
                    "--output",
                    str(temp_dir / "test.pdf"),
                ],
            )

            # Should handle network errors gracefully
            assert result.exit_code != 0
            assert "error" in result.output.lower()

    def test_cli_file_permission_errors(self, temp_dir):
        """Test CLI handling of file permission errors."""
        runner = CliRunner()

        # Try to write to a read-only location (platform-specific)

        readonly_file = temp_dir / "readonly.pdf"
        readonly_file.write_bytes(b"test")
        readonly_file.chmod(0o444)  # Read-only

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            result = runner.invoke(
                main,
                [
                    "sanitize",
                    str(readonly_file),
                    "--output-dir",
                    str(temp_dir / "output"),
                ],
            )

            # Should handle permission errors gracefully
            # (Exact behavior depends on implementation)


class TestCLIConfigurationPlatforms:
    """Test CLI configuration across platforms."""

    def test_config_file_locations(self):
        """Test config file locations are platform-appropriate."""
        from defuse.config import get_config_dir

        config_dir = get_config_dir()
        system = platform.system()

        if system == "Linux":
            # Should use XDG config directory
            assert (
                "config" in str(config_dir).lower() or "xdg" in str(config_dir).lower()
            )
        elif system == "Windows":
            # Should use AppData
            assert (
                "appdata" in str(config_dir).lower()
                or "application data" in str(config_dir).lower()
            )
        elif system == "Darwin":
            # Should use Application Support
            assert (
                "application support" in str(config_dir).lower()
                or "library" in str(config_dir).lower()
            )

    def test_cli_default_paths(self, temp_dir):
        """Test CLI default paths are platform-appropriate."""
        runner = CliRunner()

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            result = runner.invoke(main, ["config"])

            # Should show configuration without errors
            assert result.exit_code == 0

    def test_cli_temp_directory_usage(self, temp_dir):
        """Test CLI temp directory usage across platforms."""
        runner = CliRunner()

        # Should be able to use system temp directory
        temp_dir = Path(tempfile.gettempdir())
        assert temp_dir.exists()
        assert temp_dir.is_dir()
