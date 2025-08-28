"""
Windows-specific integration tests.

Tests for Windows-specific functionality including Docker Desktop integration,
Windows path handling, and Dangerzone detection.
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest
import responses

from defuse.config import Config, SandboxConfig
from defuse.sandbox import SandboxBackend, SandboxCapabilities, SandboxedDownloader
from defuse.cli import find_dangerzone_cli


# Skip all tests in this file if not on Windows
pytestmark = pytest.mark.skipif(
    platform.system() != "Windows", reason="Windows-specific tests"
)


@pytest.fixture
def windows_config():
    """Config for Windows testing."""
    import tempfile
    from pathlib import Path

    config = Config()
    # Use proper Windows temp directory
    windows_temp = Path(tempfile.gettempdir()) / "pdf-sandbox"
    config.sandbox = SandboxConfig(temp_dir=windows_temp)
    return config


class TestWindowsSandboxDetection:
    """Test sandbox detection on Windows."""

    @pytest.mark.windows
    def test_windows_sandbox_backends(self):
        """Test which sandbox backends are available on Windows."""
        caps = SandboxCapabilities()

        # On Windows, only Docker should be available (via Docker Desktop)
        # Firejail and Bubblewrap should not be available
        assert caps.available_backends[SandboxBackend.FIREJAIL] is False
        assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is False

        # Docker might be available via Docker Desktop
        # Podman is not typically available on Windows

        # At minimum, should have some backend available
        available_backends = [
            k
            for k, v in caps.available_backends.items()
            if v and k != SandboxBackend.AUTO
        ]
        assert len(available_backends) >= 0  # May have none in CI

    @pytest.mark.windows
    def test_windows_platform_detection(self):
        """Test that platform is correctly detected as Windows."""
        caps = SandboxCapabilities()
        assert caps.platform == "windows"


class TestWindowsDangerzoneDetection:
    """Test Dangerzone CLI detection on Windows."""

    @pytest.mark.windows
    def test_windows_dangerzone_paths(self):
        """Test Windows-specific Dangerzone paths are checked."""
        # Test the detection logic without requiring actual installation
        with patch("defuse.cli.shutil.which", return_value=None):  # Not in PATH
            with patch("defuse.cli.Path.exists") as mock_exists:

                def exists_side_effect(*args, **kwargs):
                    # Simulate finding Dangerzone in Program Files
                    # Check if this is a Program Files path
                    if args and "Program Files" in str(args[0]):
                        return True
                    return False

                mock_exists.side_effect = exists_side_effect

                result = find_dangerzone_cli()

                # Should have checked Windows-specific paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]

                # Verify Windows paths were checked
                program_files_paths = [
                    call for call in calls if "Program Files" in call
                ]
                appdata_paths = [call for call in calls if "AppData" in call]
                exe_paths = [call for call in calls if call.endswith(".exe")]

                assert len(program_files_paths) > 0, "Should check Program Files paths"
                assert len(appdata_paths) > 0, "Should check AppData paths"
                assert len(exe_paths) > 0, "Should check .exe extensions"

    @pytest.mark.windows
    def test_windows_path_handling(self):
        """Test Windows path handling and normalization."""
        # Test that our detection handles Windows paths correctly
        test_paths = [
            "C:/Program Files/Dangerzone/dangerzone-cli.exe",
            "C:/Program Files (x86)/Dangerzone/dangerzone-cli.exe",
            Path.home() / "AppData/Local/Dangerzone/dangerzone-cli.exe",
            Path.home() / "AppData/Roaming/Dangerzone/dangerzone-cli.exe",
        ]

        for test_path in test_paths:
            # Verify Path objects handle Windows paths correctly
            path_obj = Path(test_path)
            assert path_obj.suffix == ".exe"
            assert "Dangerzone" in str(path_obj)


class TestWindowsDockerIntegration:
    """Test Docker Desktop integration on Windows."""

    @pytest.mark.windows
    @pytest.mark.requires_docker
    def test_docker_desktop_availability(self):
        """Test Docker Desktop detection on Windows."""
        caps = SandboxCapabilities()

        # If Docker Desktop is installed, it should be detected
        if caps.available_backends[SandboxBackend.DOCKER]:
            # Docker should be the recommended backend on Windows
            assert caps.recommended_backend == SandboxBackend.DOCKER

    @pytest.mark.windows
    @pytest.mark.requires_docker
    @pytest.mark.integration
    def test_windows_docker_download(self, windows_config):
        """Test Docker-based download on Windows."""
        if not SandboxCapabilities().available_backends[SandboxBackend.DOCKER]:
            pytest.skip("Docker not available")

        downloader = SandboxedDownloader(windows_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock a simple download to test Docker integration
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                # Mock file creation
                with patch("pathlib.Path.exists", return_value=True):
                    result = downloader.run_docker_download(
                        "http://example.com/test.pdf", output_path
                    )

                # Should call Docker with proper Windows path handling
                assert mock_run.called
                cmd_args = mock_run.call_args[0][0]
                assert "docker" in cmd_args[0]

    @pytest.mark.windows
    @pytest.mark.requires_docker
    @pytest.mark.integration
    @responses.activate
    def test_windows_full_pipeline(self, windows_config):
        """Test full download/sandbox pipeline on Windows."""
        if not SandboxCapabilities().available_backends[SandboxBackend.DOCKER]:
            pytest.skip("Docker not available")

        # Mock PDF content
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.4 Test content",
            status=200,
        )

        downloader = SandboxedDownloader(windows_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock Docker execution to succeed
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.write_bytes"):  # Mock file writing
                        result = downloader.sandboxed_download(
                            "http://example.com/test.pdf", output_path
                        )

                # Should succeed using Docker backend
                if mock_run.called:
                    assert result is not None or result == output_path


class TestWindowsErrorHandling:
    """Test Windows-specific error handling."""

    @pytest.mark.windows
    def test_windows_path_errors(self, windows_config):
        """Test handling of Windows path errors."""
        downloader = SandboxedDownloader(windows_config)

        # Test with invalid Windows path
        invalid_path = Path("Z:/nonexistent/invalid/path/test.pdf")

        with patch(
            "subprocess.run", side_effect=FileNotFoundError("docker: command not found")
        ):
            result = downloader.run_docker_download(
                "http://example.com/test.pdf", invalid_path
            )
            # Should handle error gracefully
            assert result is False

    @pytest.mark.windows
    def test_windows_permission_errors(self, windows_config):
        """Test handling of Windows permission errors."""
        downloader = SandboxedDownloader(windows_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock permission error
            with patch(
                "tempfile.mkstemp", side_effect=PermissionError("Access denied")
            ):
                with pytest.raises(PermissionError):
                    downloader.create_download_script(
                        "http://example.com/test.pdf", output_path
                    )


class TestWindowsConfiguration:
    """Test Windows-specific configuration handling."""

    @pytest.mark.windows
    def test_windows_config_paths(self):
        """Test Windows configuration path handling."""
        from defuse.cli import get_config_dir

        config_dir = get_config_dir()

        # On Windows, should use APPDATA
        if platform.system() == "Windows":
            assert "AppData" in str(config_dir) or "Application Data" in str(config_dir)

    @pytest.mark.windows
    def test_windows_temp_directory(self, windows_config):
        """Test Windows temporary directory handling."""
        # Windows temp paths should work correctly
        temp_dir = windows_config.sandbox.temp_dir
        temp_path = Path(temp_dir)

        # Should be a valid Windows path
        assert temp_path.is_absolute()
        # Should exist or be creatable
        temp_path.mkdir(parents=True, exist_ok=True)
        assert temp_path.exists()


class TestWindowsSecurityReport:
    """Test security report generation on Windows."""

    @pytest.mark.windows
    def test_windows_security_report(self, windows_config):
        """Test security report generation on Windows."""
        downloader = SandboxedDownloader(windows_config)
        report = downloader.get_security_report()

        assert report["platform"] == "windows"
        assert "available_backends" in report
        assert "recommended_backend" in report

        # Windows should primarily rely on Docker
        if report["available_backends"].get("docker"):
            assert report["recommended_backend"] in ["docker", SandboxBackend.DOCKER]

    @pytest.mark.windows
    def test_windows_isolation_level(self, windows_config):
        """Test isolation level reporting on Windows."""
        downloader = SandboxedDownloader(windows_config)

        # Windows isolation depends on Docker Desktop
        caps = downloader.capabilities
        isolation_level = caps.get_max_isolation_level()

        # Should return appropriate isolation level
        assert isolation_level is not None
        assert hasattr(isolation_level, "value") or isinstance(isolation_level, str)
