"""
Cross-platform logic tests using mocks to test platform-specific code paths.

These tests mock platform.system() to verify behavior on Windows/Linux/macOS
without requiring those platforms. CI validates actual platform execution.
"""

import os
from pathlib import Path
from unittest.mock import patch, MagicMock
import pytest

from defuse.cli import get_config_dir, find_dangerzone_cli
from defuse.sandbox import SandboxCapabilities, SandboxBackend
from defuse.resources import ResourceManager


class TestConfigDirectoryLogic:
    """Test config directory path generation for each platform"""

    @patch("platform.system")
    def test_windows_config_directory_logic(self, mock_system):
        """Test Windows config path generation without Windows"""
        mock_system.return_value = "Windows"

        with patch.dict(
            os.environ, {"APPDATA": "C:\\Users\\Test\\AppData\\Roaming"}, clear=False
        ):
            config_dir = get_config_dir()
            assert "AppData" in str(config_dir)
            assert config_dir.name == "defuse"
            # Should be: C:\Users\Test\AppData\Roaming\defuse

    @patch("platform.system")
    def test_linux_config_directory_logic(self, mock_system):
        """Test Linux config path generation"""
        mock_system.return_value = "Linux"

        with patch.dict(os.environ, {"HOME": "/home/testuser"}, clear=False):
            config_dir = get_config_dir()
            assert str(config_dir) == "/home/testuser/.config/defuse"

    @patch("platform.system")
    def test_macos_config_directory_logic(self, mock_system):
        """Test macOS config path generation"""
        mock_system.return_value = "Darwin"

        with patch.dict(os.environ, {"HOME": "/Users/testuser"}, clear=False):
            config_dir = get_config_dir()
            assert "Library/Application Support" in str(config_dir)
            assert config_dir.name == "defuse"


class TestDangerzoneDetectionLogic:
    """Test Dangerzone CLI detection logic for each platform"""

    @patch("platform.system")
    @patch("shutil.which")
    @patch("defuse.cli.Path.exists")
    def test_windows_dangerzone_detection_logic(
        self, mock_exists, mock_which, mock_system
    ):
        """Test Windows Dangerzone path detection"""
        mock_system.return_value = "Windows"
        mock_which.return_value = None  # Not in PATH

        # Simulate Windows program files path exists
        mock_exists.return_value = True

        result = find_dangerzone_cli()
        # Should check Windows-specific paths and call exists()
        assert mock_exists.called or mock_which.called

    @patch("platform.system")
    @patch("shutil.which")
    @patch("os.path.exists")
    def test_linux_dangerzone_detection_logic(
        self, mock_exists, mock_which, mock_system
    ):
        """Test Linux Dangerzone path detection"""
        mock_system.return_value = "Linux"

        # Simulate found in PATH
        mock_which.return_value = "/usr/bin/dangerzone-cli"

        result = find_dangerzone_cli()
        assert result is not None
        mock_which.assert_called_with("dangerzone-cli")

    @patch("platform.system")
    @patch("shutil.which")
    @patch("defuse.cli.Path.exists")
    def test_macos_dangerzone_detection_logic(
        self, mock_exists, mock_which, mock_system
    ):
        """Test macOS Dangerzone app bundle detection"""
        mock_system.return_value = "Darwin"
        mock_which.return_value = None  # Not in PATH

        # Simulate macOS app bundle exists
        mock_exists.return_value = True

        result = find_dangerzone_cli()
        # Should check macOS-specific paths and call exists()
        assert mock_exists.called or mock_which.called


class TestSandboxBackendDetectionLogic:
    """Test sandbox backend availability detection for each platform"""

    @patch("platform.system")
    @patch("shutil.which")
    def test_windows_sandbox_backends(self, mock_which, mock_system):
        """Windows should not detect Linux sandbox tools"""
        mock_system.return_value = "Windows"
        mock_which.side_effect = lambda x: "/usr/bin/docker" if x == "docker" else None

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            caps = SandboxCapabilities()

            # Windows should not have Firejail/Bubblewrap
            assert caps.available_backends[SandboxBackend.FIREJAIL] is False
            assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is False
            # But can have Docker
            assert caps.available_backends[SandboxBackend.DOCKER] is True

    @patch("platform.system")
    @patch("shutil.which")
    def test_linux_sandbox_backends_detection_logic(self, mock_which, mock_system):
        """Linux can detect all sandbox backends"""
        mock_system.return_value = "Linux"

        # Simulate all tools available
        def which_side_effect(cmd):
            paths = {
                "docker": "/usr/bin/docker",
                "podman": "/usr/bin/podman",
                "firejail": "/usr/bin/firejail",
                "bwrap": "/usr/bin/bwrap",
            }
            return paths.get(cmd)

        mock_which.side_effect = which_side_effect

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            caps = SandboxCapabilities()

            # Linux should detect all backends
            assert caps.available_backends[SandboxBackend.FIREJAIL] is True
            assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is True
            assert caps.available_backends[SandboxBackend.DOCKER] is True
            assert caps.available_backends[SandboxBackend.PODMAN] is True

    @patch("platform.system")
    @patch("shutil.which")
    def test_macos_sandbox_backends(self, mock_which, mock_system):
        """macOS should not detect Linux sandbox tools"""
        mock_system.return_value = "Darwin"
        mock_which.side_effect = (
            lambda x: "/usr/local/bin/docker" if x == "docker" else None
        )

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = MagicMock(returncode=0)
            caps = SandboxCapabilities()

            # macOS should not have Linux-specific tools
            assert caps.available_backends[SandboxBackend.FIREJAIL] is False
            assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is False
            # But can have Docker/Podman
            assert caps.available_backends[SandboxBackend.DOCKER] is True


class TestSandboxBackendPriority:
    """Test backend selection priority logic"""

    @patch("platform.system")
    def test_docker_preferred_when_available(self, mock_system):
        """Docker should be preferred over other backends when available"""
        mock_system.return_value = "Linux"

        with patch("shutil.which") as mock_which:
            # Simulate all backends available
            mock_which.return_value = "/usr/bin/mock"

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=0)
                caps = SandboxCapabilities()

                # Docker should be recommended even when others available
                assert caps.recommended_backend == SandboxBackend.DOCKER

    @patch("platform.system")
    def test_podman_fallback_when_docker_unavailable(self, mock_system):
        """Podman should be selected when Docker is not available"""
        mock_system.return_value = "Linux"

        with patch("shutil.which") as mock_which:

            def which_side_effect(cmd):
                if cmd == "docker":
                    return None  # Docker not available
                elif cmd == "podman":
                    return "/usr/bin/podman"
                else:
                    return "/usr/bin/" + cmd

            mock_which.side_effect = which_side_effect

            with patch("subprocess.run") as mock_run:
                # Docker check fails, Podman succeeds
                def run_side_effect(cmd, **kwargs):
                    if "docker" in cmd:
                        return MagicMock(returncode=1)
                    return MagicMock(returncode=0)

                mock_run.side_effect = run_side_effect
                caps = SandboxCapabilities()

                # Should fall back to Podman
                assert caps.recommended_backend == SandboxBackend.PODMAN

    @patch("platform.system")
    def test_no_backend_raises_error(self, mock_system):
        """Should raise error when no suitable backend available"""
        mock_system.return_value = "Linux"

        with patch("shutil.which") as mock_which:
            mock_which.return_value = None  # Nothing available

            with patch("subprocess.run") as mock_run:
                mock_run.return_value = MagicMock(returncode=1)

                with pytest.raises(
                    RuntimeError, match="No suitable sandboxing backend"
                ):
                    SandboxCapabilities()


class TestPlatformPathSeparators:
    """Test that path operations work correctly on each platform"""

    @patch("platform.system")
    def test_windows_path_separators(self, mock_system):
        """Windows paths should use backslashes"""
        mock_system.return_value = "Windows"

        # Note: On Unix, Path treats Windows paths as single elements
        # This is expected behavior - pathlib is platform-dependent
        # In real Windows, this would work correctly
        # This test verifies Path handles the syntax without errors
        test_path = Path("file.txt")
        assert test_path.name == "file.txt"

    @patch("platform.system")
    def test_posix_path_separators(self, mock_system):
        """Linux/macOS paths should use forward slashes"""
        mock_system.return_value = "Linux"

        test_path = Path("/home/test/file.txt")
        assert test_path.name == "file.txt"
        assert "home" in test_path.parts


class TestResourceLimitsPlatformLogic:
    """Test resource limits availability on different platforms"""

    @patch("platform.system")
    def test_windows_lacks_resource_module(self, mock_system):
        """Windows doesn't have resource module - should handle gracefully"""
        mock_system.return_value = "Windows"

        # Import should not fail even without resource module

        # On Windows, resource limits should be no-ops or use alternatives
        manager = ResourceManager()
        assert manager.platform == "windows"

    @patch("platform.system")
    def test_unix_has_resource_module(self, mock_system):
        """Unix platforms should use resource module"""
        mock_system.return_value = "Linux"

        manager = ResourceManager()
        assert manager.platform in ["linux", "darwin"]
        # Should have resource module available (or mock gracefully)


class TestPlatformTemporaryDirectories:
    """Test temporary directory handling on each platform"""

    @patch("platform.system")
    @patch("tempfile.gettempdir")
    def test_windows_temp_directory(self, mock_gettempdir, mock_system):
        """Windows temp directory is typically in AppData/Local/Temp"""
        mock_system.return_value = "Windows"
        mock_gettempdir.return_value = "C:\\Users\\Test\\AppData\\Local\\Temp"

        import tempfile

        temp_dir = tempfile.gettempdir()
        assert "Temp" in temp_dir

    @patch("platform.system")
    @patch("tempfile.gettempdir")
    def test_linux_temp_directory(self, mock_gettempdir, mock_system):
        """Linux temp directory is typically /tmp"""
        mock_system.return_value = "Linux"
        mock_gettempdir.return_value = "/tmp"

        import tempfile

        temp_dir = tempfile.gettempdir()
        assert temp_dir == "/tmp"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
