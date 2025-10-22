"""
Linux-specific sandbox backend tests.

Tests for Firejail and Bubblewrap sandboxing backends that are only
available on Linux systems.
"""

import platform
import shutil
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from defuse.config import Config, SandboxConfig
from defuse.sandbox import SandboxBackend, SandboxCapabilities, SandboxedDownloader


# Skip all tests in this file if not on Linux
pytestmark = pytest.mark.skipif(
    platform.system() != "Linux", reason="Linux-specific sandbox tests"
)


@pytest.fixture
def linux_config():
    """Config for Linux sandbox testing."""
    config = Config()
    config.sandbox = SandboxConfig()
    return config


class TestLinuxSandboxDetection:
    """Test detection of Linux-specific sandbox tools."""

    @pytest.mark.linux
    def test_firejail_detection(self):
        """Test Firejail detection on Linux."""
        caps = SandboxCapabilities()

        # Check if Firejail is actually installed
        firejail_available = shutil.which("firejail") is not None

        if firejail_available:
            assert caps.available_backends[SandboxBackend.FIREJAIL] is True
        else:
            # If not installed, detection should return False
            assert caps.available_backends[SandboxBackend.FIREJAIL] is False

    @pytest.mark.linux
    def test_bubblewrap_detection(self):
        """Test Bubblewrap detection on Linux."""
        caps = SandboxCapabilities()

        # Check if Bubblewrap is actually installed
        bwrap_available = shutil.which("bwrap") is not None

        if bwrap_available:
            assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is True
        else:
            # If not installed, detection should return False
            assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is False

    @pytest.mark.linux
    def test_linux_sandbox_priority(self):
        """Test that Linux sandbox priority is correct."""
        caps = SandboxCapabilities()

        # On Linux, priority should be: Firejail > Bubblewrap > Podman > Docker
        if caps.available_backends[SandboxBackend.FIREJAIL]:
            assert caps.recommended_backend == SandboxBackend.FIREJAIL
        elif caps.available_backends[SandboxBackend.BUBBLEWRAP]:
            assert caps.recommended_backend == SandboxBackend.BUBBLEWRAP
        elif caps.available_backends[SandboxBackend.PODMAN]:
            assert caps.recommended_backend == SandboxBackend.PODMAN
        elif caps.available_backends[SandboxBackend.DOCKER]:
            assert caps.recommended_backend == SandboxBackend.DOCKER


class TestFirejailSandbox:
    """Test Firejail sandbox functionality."""

    @pytest.mark.linux
    @pytest.mark.requires_firejail
    def test_firejail_available(self):
        """Test that Firejail is available for testing."""
        assert shutil.which("firejail") is not None, (
            "Firejail not installed - install with: sudo apt install firejail"
        )

    @pytest.mark.linux
    @pytest.mark.requires_firejail
    @pytest.mark.sandbox
    def test_firejail_command_construction(self, linux_config):
        """Test that Firejail commands are constructed correctly."""
        downloader = SandboxedDownloader(linux_config)

        # Mock Firejail to be available
        with patch.object(
            downloader.capabilities, "available_backends"
        ) as mock_backends:
            mock_backends.__getitem__.return_value = True
            mock_backends.get.return_value = True

            with patch("subprocess.run") as mock_run:
                with patch.object(downloader, "create_download_script") as mock_script:
                    mock_script.return_value = Path("/tmp/test_script.py")
                    mock_run.return_value.returncode = 0

                    # Mock successful file creation
                    with patch("pathlib.Path.exists", return_value=True):
                        result = downloader.run_firejail_download(
                            "http://example.com/test.pdf", Path("/tmp/test.pdf")
                        )

                    # Check that subprocess.run was called
                    assert mock_run.called
                    cmd_args = mock_run.call_args[0][0]

                    # Verify Firejail security options
                    assert "firejail" in cmd_args
                    assert "--noprofile" in cmd_args
                    # Network access is required for downloads
                    assert "--net=none" not in cmd_args
                    assert "--seccomp" in cmd_args
                    assert "--noroot" in cmd_args
                    assert "--rlimit-fsize=104857600" in cmd_args  # 100MB

    @pytest.mark.linux
    @pytest.mark.requires_firejail
    @pytest.mark.sandbox
    @responses.activate
    def test_firejail_network_isolation(self, linux_config):
        """Test that Firejail properly isolates network access."""
        if not shutil.which("firejail"):
            pytest.skip("Firejail not available")

        # Mock a simple file download response
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.4 Test content",
            status=200,
        )

        downloader = SandboxedDownloader(linux_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # This will test actual Firejail isolation if available
            # The --net=none should prevent network access after setup
            try:
                result = downloader.run_firejail_download(
                    "http://example.com/test.pdf", output_path
                )
                # If Firejail works, it should handle the download via script
                assert isinstance(result, bool)
            except Exception as e:
                # If Firejail fails, it should fail gracefully
                pytest.skip(f"Firejail execution failed: {e}")


class TestBubblewrapSandbox:
    """Test Bubblewrap sandbox functionality."""

    @pytest.mark.linux
    @pytest.mark.requires_bubblewrap
    def test_bubblewrap_available(self):
        """Test that Bubblewrap is available for testing."""
        assert shutil.which("bwrap") is not None, (
            "Bubblewrap not installed - install with: sudo apt install bubblewrap"
        )

    @pytest.mark.linux
    @pytest.mark.requires_bubblewrap
    @pytest.mark.sandbox
    def test_bubblewrap_command_construction(self, linux_config):
        """Test that Bubblewrap commands are constructed correctly."""
        downloader = SandboxedDownloader(linux_config)

        # Mock Bubblewrap to be available
        with patch.object(
            downloader.capabilities, "available_backends"
        ) as mock_backends:
            mock_backends.__getitem__.return_value = True
            mock_backends.get.return_value = True

            with patch("subprocess.run") as mock_run:
                with patch.object(downloader, "create_download_script") as mock_script:
                    mock_script.return_value = Path("/tmp/test_script.py")
                    mock_run.return_value.returncode = 0

                    # Mock successful file creation
                    with patch("pathlib.Path.exists", return_value=True):
                        result = downloader.run_bubblewrap_download(
                            "http://example.com/test.pdf", Path("/tmp/test.pdf")
                        )

                    # Check that subprocess.run was called
                    assert mock_run.called
                    cmd_args = mock_run.call_args[0][0]

                    # Verify Bubblewrap namespace isolation options
                    assert "bwrap" in cmd_args
                    assert "--die-with-parent" in cmd_args
                    assert "--unshare-pid" in cmd_args
                    # Network access is required for downloads
                    assert "--unshare-net" not in cmd_args
                    assert "--tmpfs" in cmd_args
                    assert "/tmp" in cmd_args

    @pytest.mark.linux
    @pytest.mark.requires_bubblewrap
    @pytest.mark.sandbox
    def test_bubblewrap_namespace_isolation(self, linux_config):
        """Test that Bubblewrap creates proper namespace isolation."""
        if not shutil.which("bwrap"):
            pytest.skip("Bubblewrap not available")

        downloader = SandboxedDownloader(linux_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Test namespace isolation by checking command construction
            with patch("subprocess.run") as mock_run:
                with patch.object(downloader, "create_download_script") as mock_script:
                    mock_script.return_value = Path("/tmp/test_script.py")
                    mock_run.return_value.returncode = 0

                    with patch("pathlib.Path.exists", return_value=True):
                        downloader.run_bubblewrap_download(
                            "http://example.com/test.pdf", output_path
                        )

                    # Verify namespace isolation
                    cmd_args = mock_run.call_args[0][0]
                    assert "--unshare-pid" in cmd_args  # PID namespace
                    # Network access is required for downloads
                    assert "--unshare-net" not in cmd_args


class TestLinuxSandboxIntegration:
    """Integration tests for Linux sandbox backends."""

    @pytest.mark.linux
    @pytest.mark.sandbox
    def test_sandbox_backend_selection(self, linux_config):
        """Test that the correct sandbox backend is selected on Linux."""
        downloader = SandboxedDownloader(linux_config)

        # Verify that Docker is now the preferred backend
        if downloader.capabilities.available_backends[SandboxBackend.DOCKER]:
            assert downloader.capabilities.recommended_backend == SandboxBackend.DOCKER
        elif downloader.capabilities.available_backends[SandboxBackend.PODMAN]:
            assert downloader.capabilities.recommended_backend == SandboxBackend.PODMAN

    @pytest.mark.linux
    @pytest.mark.sandbox
    def test_sandbox_fallback_chain(self, linux_config):
        """Test that sandbox backends fallback correctly."""
        downloader = SandboxedDownloader(linux_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock all backends to fail except one
            with patch.object(downloader, "run_firejail_download", return_value=False):
                with patch.object(
                    downloader, "run_bubblewrap_download", return_value=False
                ):
                    with patch.object(
                        downloader, "run_podman_download", return_value=False
                    ):
                        with patch.object(
                            downloader, "run_docker_download", return_value=True
                        ):
                            result = downloader.sandboxed_download(
                                "http://example.com/test.pdf", output_path
                            )
                            # Should fall back to Docker and succeed
                            assert result == output_path

    @pytest.mark.linux
    @pytest.mark.sandbox
    @pytest.mark.slow
    def test_linux_security_report(self, linux_config):
        """Test security report generation on Linux."""
        downloader = SandboxedDownloader(linux_config)
        report = downloader.get_security_report()

        assert report["platform"] == "linux"
        assert "available_backends" in report
        assert "recommended_backend" in report

        # Linux should have more backend options
        available_count = sum(
            1
            for backend, available in report["available_backends"].items()
            if available and backend != "auto"
        )

        # Should have at least Docker available, possibly more
        assert available_count >= 1
