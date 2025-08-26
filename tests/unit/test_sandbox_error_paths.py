"""
Unit tests for sandbox error paths and exception handling.

These tests focus on error conditions, timeouts, and edge cases
in the sandbox detection and container runtime checking.
"""

import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from defuse.config import Config, SandboxConfig
from defuse.sandbox import SandboxBackend, SandboxCapabilities, SandboxedDownloader


class TestSandboxCapabilitiesErrorPaths:
    """Test error handling in sandbox capability detection."""

    def test_docker_detection_timeout(self):
        """Test Docker detection when command times out."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            # Only Docker exists in PATH, other tools don't exist
            def mock_which_side_effect(cmd):
                return "/usr/bin/docker" if cmd == "docker" else None

            mock_which.side_effect = mock_which_side_effect

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("docker", 5)

                with pytest.raises(
                    RuntimeError, match="No suitable sandboxing backend"
                ):
                    SandboxCapabilities()

    def test_docker_detection_file_not_found(self):
        """Test Docker detection when docker command doesn't exist."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            mock_which.return_value = None  # Docker not in PATH

            with pytest.raises(RuntimeError, match="No suitable sandboxing backend"):
                SandboxCapabilities()

    def test_docker_detection_process_error(self):
        """Test Docker detection when docker info fails."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            # Docker found but podman available as fallback
            def mock_which_side_effect(cmd):
                if cmd == "docker":
                    return "/usr/bin/docker"
                elif cmd == "podman":
                    return "/usr/bin/podman"
                else:
                    return None

            mock_which.side_effect = mock_which_side_effect

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                # Docker fails, podman succeeds
                def mock_run_side_effect(cmd, **kwargs):
                    if "docker" in str(cmd):
                        raise subprocess.CalledProcessError(1, "docker")
                    elif "podman" in str(cmd):
                        result = MagicMock()
                        result.returncode = 0
                        return result

                mock_run.side_effect = mock_run_side_effect

                capabilities = SandboxCapabilities()

                # Should handle docker command failure gracefully
                assert not capabilities.available_backends[SandboxBackend.DOCKER]
                assert capabilities.available_backends[SandboxBackend.PODMAN]

    def test_podman_detection_timeout(self):
        """Test Podman detection when command times out."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            # Podman found, docker available as fallback
            def mock_which_side_effect(cmd):
                if cmd == "podman":
                    return "/usr/bin/podman"
                elif cmd == "docker":
                    return "/usr/bin/docker"
                else:
                    return None

            mock_which.side_effect = mock_which_side_effect

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                # Podman times out, docker succeeds
                def mock_run_side_effect(cmd, **kwargs):
                    if "podman" in str(cmd):
                        raise subprocess.TimeoutExpired("podman", 5)
                    elif "docker" in str(cmd):
                        result = MagicMock()
                        result.returncode = 0
                        return result

                mock_run.side_effect = mock_run_side_effect

                capabilities = SandboxCapabilities()

                # Should handle timeout gracefully
                assert isinstance(capabilities.available_backends, dict)
                assert not capabilities.available_backends[SandboxBackend.PODMAN]
                assert capabilities.available_backends[SandboxBackend.DOCKER]

    def test_podman_detection_file_not_found(self):
        """Test Podman detection when podman command doesn't exist."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            # Mock which() calls for different commands
            def mock_which_side_effect(cmd):
                if cmd == "podman":
                    return None
                elif cmd == "docker":
                    return "/usr/bin/docker"  # Docker exists but podman doesn't
                return None

            mock_which.side_effect = mock_which_side_effect

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                # Docker succeeds since podman not found
                result = MagicMock()
                result.returncode = 0
                mock_run.return_value = result

                capabilities = SandboxCapabilities()

                # Should handle missing podman gracefully
                assert not capabilities.available_backends[SandboxBackend.PODMAN]
                assert capabilities.available_backends[SandboxBackend.DOCKER]

    def test_backend_detection_mixed_failures(self):
        """Test when some backends fail and others succeed."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            # Docker exists, podman doesn't
            def mock_which_side_effect(cmd):
                if cmd == "docker":
                    return "/usr/bin/docker"
                else:
                    return None

            mock_which.side_effect = mock_which_side_effect

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                # Docker succeeds, other commands would fail
                def mock_run_side_effect(cmd, **kwargs):
                    if "docker" in str(cmd):
                        result = MagicMock()
                        result.returncode = 0
                        return result
                    else:
                        raise FileNotFoundError()

                mock_run.side_effect = mock_run_side_effect

                capabilities = SandboxCapabilities()

                # Should have docker available but not others
                assert capabilities.available_backends[SandboxBackend.DOCKER]
                assert not capabilities.available_backends[SandboxBackend.PODMAN]

    def test_no_backends_available_error(self):
        """Test error when no backends are available."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            mock_which.return_value = None  # No commands found

            with pytest.raises(RuntimeError, match="No suitable sandboxing backend"):
                SandboxCapabilities()

    def test_docker_detection_success_case(self):
        """Test successful Docker detection."""
        with patch("defuse.sandbox.shutil.which") as mock_which:
            mock_which.return_value = "/usr/bin/docker"

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                result = MagicMock()
                result.returncode = 0
                mock_run.return_value = result

                capabilities = SandboxCapabilities()

                # Should successfully detect Docker
                assert capabilities.available_backends[SandboxBackend.DOCKER]

    def test_linux_specific_backend_detection_on_other_platform(self):
        """Test Linux-specific backend detection on non-Linux platform."""
        with patch("platform.system") as mock_platform:
            mock_platform.return_value = "Darwin"  # macOS

            with patch("defuse.sandbox.shutil.which") as mock_which:
                # Docker available
                def mock_which_side_effect(cmd):
                    if cmd == "docker":
                        return "/usr/bin/docker"
                    return None

                mock_which.side_effect = mock_which_side_effect

                with patch("defuse.sandbox.subprocess.run") as mock_run:
                    result = MagicMock()
                    result.returncode = 0
                    mock_run.return_value = result

                    capabilities = SandboxCapabilities()

                    # Linux-specific tools should be False on non-Linux
                    assert not capabilities.available_backends[SandboxBackend.FIREJAIL]
                    assert not capabilities.available_backends[
                        SandboxBackend.BUBBLEWRAP
                    ]
                    assert capabilities.available_backends[SandboxBackend.DOCKER]


class TestSandboxedDownloaderErrorPaths:
    """Test error handling in SandboxedDownloader."""

    def test_create_download_script_permission_error(self):
        """Test handling of permission errors when creating download scripts."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            with patch("tempfile.mkstemp") as mock_mkstemp:
                mock_mkstemp.side_effect = PermissionError("Permission denied")

                with pytest.raises(PermissionError):
                    downloader.create_download_script(
                        "http://example.com/test.pdf", Path("/tmp/test.pdf")
                    )

    def test_sandboxed_download_cleanup_on_failure(self):
        """Test that temporary files are cleaned up on download failure."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            # Mock all backend methods to return False (failure)
            with patch.object(downloader, "run_docker_download", return_value=False):
                with patch.object(
                    downloader, "run_podman_download", return_value=False
                ):
                    with patch.object(
                        downloader, "run_firejail_download", return_value=False
                    ):
                        with patch.object(
                            downloader, "run_bubblewrap_download", return_value=False
                        ):
                            # Create a temporary output file to test cleanup
                            temp_output = Path("/tmp/test_download.pdf")
                            temp_output.write_text("test content")

                            with patch("pathlib.Path.exists", return_value=True):
                                with patch("pathlib.Path.unlink") as mock_unlink:
                                    result = downloader.sandboxed_download(
                                        "http://example.com/test.pdf", temp_output
                                    )

                                    # Should return None on failure
                                    assert result is None
                                    # Should attempt cleanup
                                    mock_unlink.assert_called()

    def test_docker_download_subprocess_timeout(self):
        """Test Docker download handling subprocess timeout."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("docker", 150)

                result = downloader.run_docker_download(
                    "http://example.com/test.pdf", Path("/tmp/test.pdf")
                )

                assert result is False

    def test_docker_download_subprocess_error(self):
        """Test Docker download handling subprocess errors."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("docker: command not found")

                result = downloader.run_docker_download(
                    "http://example.com/test.pdf", Path("/tmp/test.pdf")
                )

                assert result is False

    def test_podman_download_subprocess_timeout(self):
        """Test Podman download handling subprocess timeout."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            with patch("defuse.sandbox.subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("podman", 150)

                result = downloader.run_podman_download(
                    "http://example.com/test.pdf", Path("/tmp/test.pdf")
                )

                assert result is False

    def test_security_report_with_string_enums(self):
        """Test security report generation when backends are strings instead of enums."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities") as mock_caps:
            # Mock capabilities with string values (edge case)
            mock_caps_instance = MagicMock()
            mock_caps_instance.platform = "linux"
            mock_caps_instance.available_backends = {"docker": True, "podman": False}
            mock_caps_instance.recommended_backend = "docker"  # String instead of enum
            mock_caps_instance.get_max_isolation_level.return_value = "strict"
            mock_caps.return_value = mock_caps_instance

            downloader = SandboxedDownloader(config)

            # Should handle string values gracefully
            report = downloader.get_security_report()

            assert isinstance(report, dict)
            assert "platform" in report
            assert "available_backends" in report
            assert "recommended_backend" in report

    def test_enum_parsing_invalid_values(self):
        """Test enum parsing with invalid configuration values."""
        config = Config()
        config.sandbox = SandboxConfig()
        config.sandbox.isolation_level = "invalid_level"  # Invalid enum value
        config.sandbox.sandbox_backend = "invalid_backend"  # Invalid enum value

        with patch("defuse.sandbox.SandboxCapabilities"):
            # Should handle invalid enum values gracefully and use defaults
            downloader = SandboxedDownloader(config)

            # Should have default values despite invalid config
            assert downloader.isolation_level is not None
            assert downloader.backend is not None


class TestContainerRuntimeChecking:
    """Test container runtime checking edge cases."""

    def test_script_creation_with_special_characters(self):
        """Test download script creation with URLs containing special characters."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            # URL with special characters that might break script generation
            special_url = "http://example.com/file%20with%20spaces&params=test"

            with patch("tempfile.mkstemp") as mock_mkstemp:
                with patch("os.fdopen") as mock_fdopen:
                    mock_fd = MagicMock()
                    mock_fdopen.return_value.__enter__ = lambda x: mock_fd
                    mock_fdopen.return_value.__exit__ = lambda x, y, z, w: None
                    mock_mkstemp.return_value = (1, "/tmp/script.py")

                    script_path = downloader.create_download_script(
                        special_url, Path("/tmp/output.pdf")
                    )

                    # Should succeed without throwing exceptions
                    assert script_path == Path("/tmp/script.py")

    def test_firejail_download_script_cleanup_on_error(self):
        """Test that firejail download cleans up scripts on error."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            mock_script = MagicMock()
            mock_script_path = Path("/tmp/script.py")

            with patch.object(downloader, "create_download_script") as mock_create:
                mock_create.return_value = mock_script_path

                with patch("defuse.sandbox.subprocess.run") as mock_run:
                    mock_run.side_effect = Exception("Firejail error")

                    with patch("pathlib.Path.unlink") as mock_unlink:
                        result = downloader.run_firejail_download(
                            "http://example.com/test.pdf", Path("/tmp/output.pdf")
                        )

                        assert result is False
                        # Should clean up script even on error
                        mock_unlink.assert_called()

    def test_bubblewrap_download_script_cleanup_on_error(self):
        """Test that bubblewrap download cleans up scripts on error."""
        config = Config()
        config.sandbox = SandboxConfig()

        with patch("defuse.sandbox.SandboxCapabilities"):
            downloader = SandboxedDownloader(config)

            mock_script_path = Path("/tmp/script.py")

            with patch.object(downloader, "create_download_script") as mock_create:
                mock_create.return_value = mock_script_path

                with patch("defuse.sandbox.subprocess.run") as mock_run:
                    mock_run.side_effect = subprocess.TimeoutExpired("bwrap", 120)

                    with patch("pathlib.Path.unlink") as mock_unlink:
                        result = downloader.run_bubblewrap_download(
                            "http://example.com/test.pdf", Path("/tmp/output.pdf")
                        )

                        assert result is False
                        # Should clean up script even on timeout
                        mock_unlink.assert_called()
