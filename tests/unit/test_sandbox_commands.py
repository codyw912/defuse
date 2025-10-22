"""
Test sandbox command construction logic without actually executing commands.

These tests verify that sandbox backends build correct command structures
using mocks, without requiring the actual sandbox tools to be installed.
"""

import platform
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from defuse.config import Config
from defuse.sandbox import SandboxBackend, SandboxedDownloader


class TestFirejailCommandConstruction:
    """Test Firejail command building logic"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_firejail_command_has_required_flags(self, mock_run, mock_which):
        """Verify Firejail command includes all security flags"""
        mock_which.side_effect = (
            lambda x: "/usr/bin/" + x if x in ["docker", "firejail"] else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.FIREJAIL

        # Mock that Firejail is available
        downloader.capabilities.available_backends[SandboxBackend.FIREJAIL] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_firejail_download(
            "http://test.com/file.pdf", output_path
        )

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Verify command structure
            assert call_args[0] == "firejail"
            assert "--noprofile" in call_args
            assert "--seccomp" in call_args
            assert "--noroot" in call_args
            assert "--private-tmp" in call_args
            assert "--private-dev" in call_args

            # Verify resource limits are set
            assert any("--rlimit-fsize" in str(arg) for arg in call_args)
            assert any("--rlimit-nofile" in str(arg) for arg in call_args)
            assert any("--timeout" in str(arg) for arg in call_args)

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_firejail_bind_mount_syntax(self, mock_run, mock_which):
        """Verify Firejail uses correct bind mount syntax"""
        mock_which.side_effect = (
            lambda x: "/usr/bin/" + x if x in ["docker", "firejail"] else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.FIREJAIL
        downloader.capabilities.available_backends[SandboxBackend.FIREJAIL] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_firejail_download(
            "http://test.com/file.pdf", output_path
        )

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Should bind mount output directory
            bind_args = [arg for arg in call_args if "--bind" in str(arg)]
            assert len(bind_args) > 0


class TestBubblewrapCommandConstruction:
    """Test Bubblewrap command building logic"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_bubblewrap_command_has_isolation_flags(self, mock_run, mock_which):
        """Verify Bubblewrap command includes isolation flags"""
        mock_which.side_effect = (
            lambda x: "/usr/bin/" + x if x in ["docker", "bwrap"] else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.BUBBLEWRAP
        downloader.capabilities.available_backends[SandboxBackend.BUBBLEWRAP] = True

        output_path = Path("/tmp/test_output.pdf")

        # Create a temp script file that would normally be created
        with patch("tempfile.mkstemp") as mock_mkstemp:
            mock_mkstemp.return_value = (1, "/tmp/fake_script.py")
            with patch("os.fdopen"):
                with patch("pathlib.Path.unlink"):
                    result = downloader.run_bubblewrap_download(
                        "http://test.com/file.pdf", output_path
                    )

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Verify command structure
            assert call_args[0] == "bwrap"
            assert "--new-session" in call_args
            assert "--die-with-parent" in call_args
            assert "--unshare-pid" in call_args


class TestDockerCommandConstruction:
    """Test Docker command building logic"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_docker_command_has_security_options(self, mock_run, mock_which):
        """Verify Docker command includes all security options"""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER
        downloader.capabilities.available_backends[SandboxBackend.DOCKER] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        if mock_run.called:
            call_args = mock_run.call_args[0][0]
            is_windows = platform.system() == "Windows"

            # Verify Docker command structure
            assert "docker" in call_args[0]
            assert "run" in call_args
            assert "--rm" in call_args

            if is_windows:
                # Windows Docker engine lacks read-only and security-opt support
                assert "--read-only" not in call_args
                assert "--security-opt" not in call_args
            else:
                assert "--read-only" in call_args

                # Verify security options
                security_opt_found = False
                for i, arg in enumerate(call_args):
                    if arg == "--security-opt" and i + 1 < len(call_args):
                        if "no-new-privileges" in call_args[i + 1]:
                            security_opt_found = True
                assert security_opt_found, (
                    "Should have --security-opt no-new-privileges"
                )

            # Verify resource limits
            memory_found = any("--memory" in str(arg) for arg in call_args)
            cpu_found = any("--cpu-shares" in str(arg) for arg in call_args)
            assert memory_found, "Should have memory limit"
            assert cpu_found, "Should have CPU limit"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_docker_tmpfs_mount_options(self, mock_run, mock_which):
        """Verify Docker tmpfs has noexec,nosuid flags"""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER
        downloader.capabilities.available_backends[SandboxBackend.DOCKER] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        if mock_run.called:
            call_args = mock_run.call_args[0][0]
            if platform.system() == "Windows":
                # tmpfs not supported on Windows Docker engine
                assert "--tmpfs" not in call_args
                return

            # Find tmpfs argument
            tmpfs_arg = None
            for i, arg in enumerate(call_args):
                if arg == "--tmpfs" and i + 1 < len(call_args):
                    tmpfs_arg = call_args[i + 1]
                    break

            assert tmpfs_arg is not None, "Should have tmpfs mount"
            assert "noexec" in tmpfs_arg, "tmpfs should have noexec"
            assert "nosuid" in tmpfs_arg, "tmpfs should have nosuid"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_docker_volume_mount_for_output(self, mock_run, mock_which):
        """Verify Docker mounts output directory correctly"""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER
        downloader.capabilities.available_backends[SandboxBackend.DOCKER] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Should have volume mount
            volume_found = False
            for i, arg in enumerate(call_args):
                if arg == "--volume" and i + 1 < len(call_args):
                    volume_arg = call_args[i + 1]
                    if "/output" in volume_arg:
                        volume_found = True
                        # Should be read-write for output
                        assert ":rw" in volume_arg or volume_arg.endswith("/output")

            assert volume_found, "Should mount output directory"


class TestPodmanCommandConstruction:
    """Test Podman command building logic"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_podman_command_structure(self, mock_run, mock_which):
        """Verify Podman command is similar to Docker with differences"""
        mock_which.side_effect = (
            lambda x: "/usr/bin/" + x if x in ["docker", "podman"] else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.PODMAN
        downloader.capabilities.available_backends[SandboxBackend.PODMAN] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_podman_download("http://test.com/file.pdf", output_path)

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Verify Podman command structure
            assert "podman" in call_args[0]
            assert "run" in call_args
            assert "--rm" in call_args

            # Podman uses --cpus instead of --cpu-shares
            cpus_found = any("--cpus" in str(arg) for arg in call_args)
            assert cpus_found, "Podman should use --cpus for CPU limits"


class TestSandboxCommandURLHandling:
    """Test that URLs are properly passed to sandbox commands"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_url_is_embedded_in_command(self, mock_run, mock_which):
        """Verify test URL appears in Docker command"""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER
        downloader.capabilities.available_backends[SandboxBackend.DOCKER] = True

        test_url = "http://example.com/test-file.pdf"
        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download(test_url, output_path)

        if mock_run.called:
            call_args = mock_run.call_args[0][0]
            full_command = " ".join(str(arg) for arg in call_args)

            # URL should be embedded in the Python command
            assert test_url in full_command, "URL should appear in command"


class TestSandboxCommandErrorHandling:
    """Test sandbox command error handling logic"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_docker_nonzero_exit_returns_false(self, mock_run, mock_which):
        """Docker failure should return False"""
        # First call for detection succeeds, second call for actual download fails
        mock_run.side_effect = [
            MagicMock(returncode=0),  # docker info check
            MagicMock(returncode=1, stderr="error"),  # actual download command
        ]
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        assert result is False, "Failed Docker command should return False"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_timeout_returns_false(self, mock_run, mock_which):
        """Timeout should be handled gracefully"""
        import subprocess

        # First call succeeds (detection), second times out
        mock_run.side_effect = [
            MagicMock(returncode=0),  # docker info check
            subprocess.TimeoutExpired("docker", 150),  # download timeout
        ]
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        assert result is False, "Timeout should return False"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_exception_returns_false(self, mock_run, mock_which):
        """General exceptions should be handled"""
        # Multiple calls: docker check, podman check, then download error
        mock_run.side_effect = [
            MagicMock(returncode=0),  # docker info check
            Exception("Unexpected error"),  # download error
        ]
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )

        config = Config()
        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        assert result is False, "Exception should return False"


class TestConfigLimitsInCommands:
    """Test that config limits are properly applied in commands"""

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_custom_memory_limit_in_docker_command(self, mock_run, mock_which):
        """Custom memory limit should appear in Docker command"""
        mock_which.side_effect = (
            lambda cmd: "/usr/bin/docker" if cmd == "docker" else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        config.sandbox.max_memory_mb = 256  # Custom limit

        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.DOCKER
        downloader.capabilities.available_backends[SandboxBackend.DOCKER] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_docker_download("http://test.com/file.pdf", output_path)

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Find memory argument
            memory_arg = None
            for i, arg in enumerate(call_args):
                if arg == "--memory" and i + 1 < len(call_args):
                    memory_arg = call_args[i + 1]

            assert memory_arg is not None, "Memory limit should be set"
            assert "256m" in memory_arg, (
                f"Should use custom 256MB limit, got {memory_arg}"
            )

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_custom_file_size_limit_in_firejail(self, mock_run, mock_which):
        """Custom file size limit should appear in Firejail command"""
        mock_which.side_effect = (
            lambda x: "/usr/bin/" + x if x in ["docker", "firejail"] else None
        )
        mock_run.return_value = MagicMock(returncode=0)

        config = Config()
        config.sandbox.max_file_size = 50 * 1024 * 1024  # 50MB

        downloader = SandboxedDownloader(config)
        downloader.backend = SandboxBackend.FIREJAIL
        downloader.capabilities.available_backends[SandboxBackend.FIREJAIL] = True

        output_path = Path("/tmp/test_output.pdf")
        result = downloader.run_firejail_download(
            "http://test.com/file.pdf", output_path
        )

        if mock_run.called:
            call_args = mock_run.call_args[0][0]

            # Should have rlimit-fsize with custom value
            fsize_found = any(
                "--rlimit-fsize=" in str(arg) and "52428800" in str(arg)
                for arg in call_args
            )
            assert fsize_found, "Should use custom file size limit"


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
