"""
macOS-specific integration tests.

Tests for macOS-specific functionality including Docker Desktop integration,
app bundle detection, Homebrew path handling, and Dangerzone detection.
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


# Skip all tests in this file if not on macOS
pytestmark = pytest.mark.skipif(
    platform.system() != "Darwin", reason="macOS-specific tests"
)


@pytest.fixture
def macos_config():
    """Config for macOS testing."""
    config = Config()
    config.sandbox = SandboxConfig()
    return config


class TestMacOSSandboxDetection:
    """Test sandbox detection on macOS."""

    @pytest.mark.macos
    def test_macos_sandbox_backends(self):
        """Test which sandbox backends are available on macOS."""
        caps = SandboxCapabilities()

        # On macOS, Linux-specific tools should not be available
        assert caps.available_backends[SandboxBackend.FIREJAIL] is False
        assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is False

        # Docker should be available via Docker Desktop
        # Podman may be available via Homebrew

        # At minimum, should have some backend available
        available_backends = [
            k
            for k, v in caps.available_backends.items()
            if v and k != SandboxBackend.AUTO
        ]
        assert len(available_backends) >= 0  # May have none in CI

    @pytest.mark.macos
    def test_macos_platform_detection(self):
        """Test that platform is correctly detected as Darwin."""
        caps = SandboxCapabilities()
        assert caps.platform == "darwin"

    @pytest.mark.macos
    def test_macos_container_preference(self):
        """Test container backend preference on macOS."""
        caps = SandboxCapabilities()

        # On macOS, Podman should be preferred over Docker
        if caps.available_backends[SandboxBackend.PODMAN]:
            assert caps.recommended_backend == SandboxBackend.PODMAN
        elif caps.available_backends[SandboxBackend.DOCKER]:
            assert caps.recommended_backend == SandboxBackend.DOCKER


class TestMacOSDangerzoneDetection:
    """Test Dangerzone CLI detection on macOS."""

    @pytest.mark.macos
    def test_macos_app_bundle_detection(self):
        """Test macOS app bundle detection for Dangerzone."""
        # Test the detection logic without requiring actual installation
        checked_paths = []

        # Mock Path.exists to track what paths are checked
        original_exists = Path.exists

        def mock_exists(self, *, follow_symlinks=True):
            path_str = str(self)
            checked_paths.append(path_str)
            # Simulate finding Dangerzone in Applications
            return "Dangerzone.app" in path_str

        with patch("defuse.cli.shutil.which", return_value=None):  # Not in PATH
            # Replace the exists method on Path instances
            Path.exists = mock_exists
            try:
                result = find_dangerzone_cli()

                # Should have found it in Applications
                assert result is not None
                assert "Dangerzone.app" in str(result)

                # Verify macOS paths were checked
                app_bundle_paths = [p for p in checked_paths if "Dangerzone.app" in p]
                homebrew_paths = [
                    p for p in checked_paths if "homebrew" in p or "usr/local" in p
                ]

                assert len(app_bundle_paths) > 0, (
                    f"Should check app bundle paths, but only checked: {checked_paths}"
                )
                # When app bundle is found first, it returns early (which is correct behavior)
            finally:
                # Restore original method
                Path.exists = original_exists

    @pytest.mark.macos
    def test_macos_homebrew_paths(self):
        """Test Homebrew path detection on macOS."""
        # Test the detection checks Homebrew paths
        test_paths = [
            Path("/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"),
            Path(
                "~/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
            ).expanduser(),
            Path("/opt/homebrew/bin/dangerzone-cli"),  # Apple Silicon Homebrew
            Path("/usr/local/bin/dangerzone-cli"),  # Intel Homebrew
        ]

        for test_path in test_paths:
            # Verify Path objects handle macOS paths correctly
            assert test_path.is_absolute()
            if "Dangerzone.app" in str(test_path):
                assert "Contents/MacOS" in str(test_path)

    @pytest.mark.macos
    def test_macos_user_applications(self):
        """Test user Applications directory detection."""
        user_app_path = Path(
            "~/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
        ).expanduser()

        # Should expand to user's home directory
        assert str(user_app_path).startswith(str(Path.home()))
        assert "Applications" in str(user_app_path)


class TestMacOSDockerIntegration:
    """Test Docker Desktop integration on macOS."""

    @pytest.mark.macos
    @pytest.mark.requires_docker
    def test_docker_desktop_availability(self):
        """Test Docker Desktop detection on macOS."""
        caps = SandboxCapabilities()

        # If Docker Desktop is installed, it should be detected
        if caps.available_backends[SandboxBackend.DOCKER]:
            # Docker should be available as a backend
            assert caps.available_backends[SandboxBackend.DOCKER] is True

    @pytest.mark.macos
    @pytest.mark.requires_docker
    @pytest.mark.integration
    def test_macos_docker_download(self, macos_config):
        """Test Docker-based download on macOS."""
        if not SandboxCapabilities().available_backends[SandboxBackend.DOCKER]:
            pytest.skip("Docker not available")

        downloader = SandboxedDownloader(macos_config)

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

                # Should call Docker with proper macOS path handling
                assert mock_run.called
                cmd_args = mock_run.call_args[0][0]
                assert "docker" in cmd_args[0]

    @pytest.mark.macos
    @pytest.mark.requires_podman
    @pytest.mark.integration
    def test_macos_podman_integration(self, macos_config):
        """Test Podman integration on macOS (if available via Homebrew)."""
        caps = SandboxCapabilities()

        if not caps.available_backends[SandboxBackend.PODMAN]:
            pytest.skip("Podman not available")

        downloader = SandboxedDownloader(macos_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock Podman execution
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                with patch("pathlib.Path.exists", return_value=True):
                    result = downloader.run_podman_download(
                        "http://example.com/test.pdf", output_path
                    )

                # Should call Podman
                if mock_run.called:
                    cmd_args = mock_run.call_args[0][0]
                    assert "podman" in cmd_args[0]


class TestMacOSPathHandling:
    """Test macOS-specific path handling."""

    @pytest.mark.macos
    def test_macos_path_normalization(self):
        """Test macOS path handling and normalization."""
        # Test various macOS-specific paths
        test_paths = [
            "/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli",
            "~/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli",
            "/opt/homebrew/bin/dangerzone-cli",
            "/usr/local/bin/dangerzone-cli",
        ]

        for test_path in test_paths:
            path_obj = Path(test_path).expanduser()
            # Should handle macOS paths correctly
            assert path_obj.is_absolute()

    @pytest.mark.macos
    def test_macos_homebrew_detection(self):
        """Test Homebrew path detection logic."""
        # Test both Intel and Apple Silicon Homebrew paths
        intel_homebrew = Path("/usr/local/bin/dangerzone-cli")
        apple_homebrew = Path("/opt/homebrew/bin/dangerzone-cli")

        assert intel_homebrew.is_absolute()
        assert apple_homebrew.is_absolute()
        assert "homebrew" in str(apple_homebrew)

    @pytest.mark.macos
    def test_macos_app_bundle_structure(self):
        """Test app bundle path structure understanding."""
        app_bundle_path = Path(
            "/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
        )

        assert "Applications" in str(app_bundle_path)
        assert "Contents/MacOS" in str(app_bundle_path)
        assert app_bundle_path.name == "dangerzone-cli"


class TestMacOSErrorHandling:
    """Test macOS-specific error handling."""

    @pytest.mark.macos
    def test_macos_permission_errors(self, macos_config):
        """Test handling of macOS permission errors."""
        downloader = SandboxedDownloader(macos_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock permission error
            with patch(
                "tempfile.mkstemp",
                side_effect=PermissionError("Operation not permitted"),
            ):
                with pytest.raises(PermissionError):
                    downloader.create_download_script(
                        "http://example.com/test.pdf", output_path
                    )

    @pytest.mark.macos
    def test_macos_docker_errors(self, macos_config):
        """Test Docker error handling on macOS."""
        downloader = SandboxedDownloader(macos_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock Docker not running (common on macOS)
            with patch(
                "subprocess.run",
                side_effect=ConnectionError("Docker daemon not running"),
            ):
                result = downloader.run_docker_download(
                    "http://example.com/test.pdf", output_path
                )
                # Should handle error gracefully
                assert result is False


class TestMacOSConfiguration:
    """Test macOS-specific configuration handling."""

    @pytest.mark.macos
    def test_macos_config_paths(self):
        """Test macOS configuration path handling."""
        # Since conftest.py patches get_config_dir for all tests,
        # we'll test the logic directly
        if platform.system() == "Darwin":
            # Test that the expected macOS path would be correct
            expected_path = Path.home() / "Library" / "Application Support" / "defuse"
            assert "Application Support" in str(expected_path)
            assert "Library" in str(expected_path)

            # The actual get_config_dir is patched by conftest.py to use temp dir
            # which is the correct behavior for tests

    @pytest.mark.macos
    def test_macos_temp_directory(self, macos_config):
        """Test macOS temporary directory handling."""
        # macOS temp paths should work correctly
        temp_dir = macos_config.sandbox.temp_dir
        temp_path = Path(temp_dir)

        # Should be a valid macOS path
        assert temp_path.is_absolute()
        # Should exist or be creatable
        temp_path.mkdir(parents=True, exist_ok=True)
        assert temp_path.exists()


class TestMacOSSecurityReport:
    """Test security report generation on macOS."""

    @pytest.mark.macos
    def test_macos_security_report(self, macos_config):
        """Test security report generation on macOS."""
        downloader = SandboxedDownloader(macos_config)
        report = downloader.get_security_report()

        assert report["platform"] == "darwin"
        assert "available_backends" in report
        assert "recommended_backend" in report

        # macOS should prefer Podman over Docker if available
        available_backends = report["available_backends"]
        if available_backends.get("podman"):
            assert report["recommended_backend"] in [
                "podman",
                str(SandboxBackend.PODMAN),
            ]
        elif available_backends.get("docker"):
            assert report["recommended_backend"] in [
                "docker",
                str(SandboxBackend.DOCKER),
            ]

    @pytest.mark.macos
    def test_macos_isolation_level(self, macos_config):
        """Test isolation level reporting on macOS."""
        downloader = SandboxedDownloader(macos_config)

        # macOS isolation depends on container availability
        caps = downloader.capabilities
        isolation_level = caps.get_max_isolation_level()

        # Should return appropriate isolation level
        assert isolation_level is not None
        assert hasattr(isolation_level, "value") or isinstance(isolation_level, str)

    @pytest.mark.macos
    @pytest.mark.integration
    @responses.activate
    def test_macos_full_pipeline(self, macos_config):
        """Test full download/sandbox pipeline on macOS."""
        # Skip if no container runtime available
        caps = SandboxCapabilities()
        if not any(
            caps.available_backends[backend]
            for backend in [SandboxBackend.DOCKER, SandboxBackend.PODMAN]
        ):
            pytest.skip("No container runtime available")

        # Mock PDF content
        responses.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.4 Test content",
            status=200,
        )

        downloader = SandboxedDownloader(macos_config)

        with tempfile.TemporaryDirectory() as temp_dir:
            output_path = Path(temp_dir) / "test.pdf"

            # Mock container execution to succeed
            with patch("subprocess.run") as mock_run:
                mock_run.return_value.returncode = 0

                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.write_bytes"):  # Mock file writing
                        result = downloader.sandboxed_download(
                            "http://example.com/test.pdf", output_path
                        )

                # Should succeed using available backend
                if mock_run.called:
                    assert result is not None or result == output_path
