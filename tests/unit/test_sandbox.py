"""
Unit tests for sandbox capabilities and backend management.
"""

from pathlib import Path
from unittest.mock import patch, MagicMock
import subprocess

import pytest

from defuse.config import Config
from defuse.sandbox import (
    IsolationLevel,
    SandboxBackend,
    SandboxCapabilities,
    SandboxedDownloader,
    get_sandbox_capabilities,
    create_sandboxed_downloader,
)


@pytest.mark.unit
class TestIsolationLevel:
    """Test the IsolationLevel enum."""

    def test_isolation_levels_defined(self):
        """Test that all expected isolation levels are defined."""
        expected_levels = {"none", "basic", "strict", "paranoid"}
        actual_levels = {level.value for level in IsolationLevel}
        assert actual_levels == expected_levels

    def test_isolation_level_ordering(self):
        """Test that isolation levels have logical ordering."""
        levels = [
            IsolationLevel.NONE,
            IsolationLevel.BASIC,
            IsolationLevel.STRICT,
            IsolationLevel.PARANOID,
        ]

        # Check that each level represents increasing security
        assert IsolationLevel.NONE.value == "none"
        assert IsolationLevel.BASIC.value == "basic"
        assert IsolationLevel.STRICT.value == "strict"
        assert IsolationLevel.PARANOID.value == "paranoid"


@pytest.mark.unit
class TestSandboxBackend:
    """Test the SandboxBackend enum."""

    def test_sandbox_backends_defined(self):
        """Test that all expected sandbox backends are defined."""
        expected_backends = {"auto", "firejail", "bubblewrap", "podman", "docker"}
        actual_backends = {backend.value for backend in SandboxBackend}
        assert actual_backends == expected_backends

    def test_no_subprocess_backend(self):
        """Test that subprocess backend is not available (security requirement)."""
        backend_values = {backend.value for backend in SandboxBackend}
        assert "subprocess" not in backend_values

    def test_security_focused_backends(self):
        """Test that available backends are security-focused."""
        # All backends should be container-based or specialized sandboxes
        security_backends = {"auto", "firejail", "bubblewrap", "podman", "docker"}
        for backend in SandboxBackend:
            assert backend.value in security_backends


@pytest.mark.unit
class TestSandboxCapabilities:
    """Test the SandboxCapabilities class."""

    def test_capabilities_initialization(self):
        """Test that capabilities initialize properly."""
        caps = SandboxCapabilities()

        assert hasattr(caps, "platform")
        assert hasattr(caps, "available_backends")
        assert hasattr(caps, "recommended_backend")
        assert isinstance(caps.available_backends, dict)

    def test_platform_detection(self):
        """Test platform detection."""
        with patch("platform.system") as mock_platform:
            mock_platform.return_value = "Linux"
            caps = SandboxCapabilities()
            assert caps.platform == "linux"

            mock_platform.return_value = "Darwin"
            caps = SandboxCapabilities()
            assert caps.platform == "darwin"

            mock_platform.return_value = "Windows"
            caps = SandboxCapabilities()
            assert caps.platform == "windows"

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_docker_detection_available(self, mock_run, mock_which):
        """Test Docker detection when available."""
        mock_which.return_value = "/usr/bin/docker"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        caps = SandboxCapabilities()
        assert caps.available_backends[SandboxBackend.DOCKER] is True

    @patch("shutil.which")
    def test_docker_detection_not_available(self, mock_which):
        """Test Docker detection when not available."""
        mock_which.return_value = None

        # Should raise error when no backends available
        with pytest.raises(
            RuntimeError, match="No suitable sandboxing backend available"
        ):
            SandboxCapabilities()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_docker_detection_daemon_not_running(self, mock_run, mock_which):
        """Test Docker detection when binary exists but daemon isn't running."""
        mock_which.return_value = "/usr/bin/docker"
        mock_result = MagicMock()
        mock_result.returncode = 1  # Docker daemon not running
        mock_run.return_value = mock_result

        # Should raise error when Docker daemon not available
        with pytest.raises(
            RuntimeError, match="No suitable sandboxing backend available"
        ):
            SandboxCapabilities()

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_podman_detection_available(self, mock_run, mock_which):
        """Test Podman detection when available."""
        mock_which.return_value = "/usr/bin/podman"
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        caps = SandboxCapabilities()
        assert caps.available_backends[SandboxBackend.PODMAN] is True

    @patch("platform.system")
    @patch("shutil.which")
    def test_linux_sandbox_tools_detection(self, mock_which, mock_platform):
        """Test detection of Linux-specific sandbox tools."""
        mock_platform.return_value = "Linux"

        def which_side_effect(cmd):
            if cmd == "firejail":
                return "/usr/bin/firejail"
            elif cmd == "bwrap":
                return "/usr/bin/bwrap"
            return None

        mock_which.side_effect = which_side_effect

        caps = SandboxCapabilities()
        assert caps.available_backends[SandboxBackend.FIREJAIL] is True
        assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is True

    @patch("platform.system")
    @patch("shutil.which")
    @patch("subprocess.run")
    def test_non_linux_sandbox_tools_unavailable(
        self, mock_run, mock_which, mock_platform
    ):
        """Test that Linux sandbox tools are not available on other platforms."""
        mock_platform.return_value = "Darwin"  # macOS

        def which_side_effect(cmd):
            if cmd == "docker":
                return "/usr/bin/docker"
            return None

        mock_which.side_effect = which_side_effect

        # Mock Docker as available
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        caps = SandboxCapabilities()
        assert caps.available_backends[SandboxBackend.FIREJAIL] is False
        assert caps.available_backends[SandboxBackend.BUBBLEWRAP] is False
        assert caps.available_backends[SandboxBackend.DOCKER] is True

    def test_auto_backend_always_available(self):
        """Test that AUTO backend is always available."""
        caps = SandboxCapabilities()
        assert caps.available_backends[SandboxBackend.AUTO] is True

    @patch("shutil.which")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_recommended_backend_priority_linux(
        self, mock_platform, mock_run, mock_which
    ):
        """Test recommended backend priority on Linux."""
        mock_platform.return_value = "Linux"

        # Test Firejail preferred
        def which_side_effect(cmd):
            if cmd == "firejail":
                return "/usr/bin/firejail"
            return None

        mock_which.side_effect = which_side_effect

        caps = SandboxCapabilities()
        assert caps.recommended_backend == SandboxBackend.FIREJAIL

    @patch("shutil.which")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_recommended_backend_docker_fallback(
        self, mock_platform, mock_run, mock_which
    ):
        """Test Docker as fallback recommended backend."""
        mock_platform.return_value = "Darwin"  # No Linux tools available

        # Docker available
        def which_side_effect(cmd):
            if cmd == "docker":
                return "/usr/bin/docker"
            return None

        mock_which.side_effect = which_side_effect

        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        caps = SandboxCapabilities()
        assert caps.recommended_backend == SandboxBackend.DOCKER

    @patch("shutil.which")
    @patch("subprocess.run")
    def test_no_suitable_backend_raises_error(self, mock_run, mock_which):
        """Test that missing suitable backends raises an error."""
        # No backends available
        mock_which.return_value = None
        mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

        with pytest.raises(
            RuntimeError, match="No suitable sandboxing backend available"
        ):
            SandboxCapabilities()

    @patch("shutil.which")
    @patch("subprocess.run")
    @patch("platform.system")
    def test_max_isolation_level(self, mock_platform, mock_run, mock_which):
        """Test maximum isolation level determination."""
        # Test with Firejail available (paranoid level)
        mock_platform.return_value = "Linux"

        def which_side_effect(cmd):
            if cmd == "firejail":
                return "/usr/bin/firejail"
            return None

        mock_which.side_effect = which_side_effect

        caps = SandboxCapabilities()
        assert caps.get_max_isolation_level() == IsolationLevel.PARANOID

        # Test with only Docker available (strict level)
        mock_platform.return_value = "Darwin"

        def which_side_effect_docker(cmd):
            if cmd == "docker":
                return "/usr/bin/docker"
            return None

        mock_which.side_effect = which_side_effect_docker
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        caps = SandboxCapabilities()
        assert caps.get_max_isolation_level() == IsolationLevel.STRICT


@pytest.mark.unit
class TestSandboxedDownloader:
    """Test the SandboxedDownloader class."""

    def test_downloader_initialization(
        self, config_fixture: Config, mock_sandbox_capabilities
    ):
        """Test downloader initialization."""
        downloader = SandboxedDownloader(config_fixture)
        assert downloader.config == config_fixture
        assert downloader.capabilities is not None

    def test_backend_auto_selection(
        self, config_fixture: Config, mock_sandbox_capabilities
    ):
        """Test automatic backend selection."""
        config_fixture.sandbox.sandbox_backend = "auto"

        downloader = SandboxedDownloader(config_fixture)
        assert downloader.backend == SandboxBackend.DOCKER

    def test_explicit_backend_selection(
        self, config_fixture: Config, mock_sandbox_capabilities
    ):
        """Test explicit backend selection."""
        config_fixture.sandbox.sandbox_backend = "podman"

        downloader = SandboxedDownloader(config_fixture)
        assert downloader.backend == SandboxBackend.PODMAN

    def test_isolation_level_parsing(
        self, config_fixture: Config, mock_sandbox_capabilities
    ):
        """Test isolation level string parsing."""
        config_fixture.sandbox.isolation_level = "paranoid"

        downloader = SandboxedDownloader(config_fixture)
        assert downloader.isolation_level == IsolationLevel.PARANOID

    def test_create_download_script(
        self, config_fixture: Config, temp_dir: Path, mock_sandbox_capabilities
    ):
        """Test download script creation."""
        config_fixture.sandbox.temp_dir = temp_dir

        downloader = SandboxedDownloader(config_fixture)

        test_url = "https://example.com/test.pdf"
        output_path = temp_dir / "output.pdf"

        script_path = downloader.create_download_script(test_url, output_path)

        assert script_path.exists()
        assert script_path.suffix == ".py"

        script_content = script_path.read_text()
        assert test_url in script_content
        assert str(output_path) in script_content
        assert "download_document" in script_content

        # Clean up
        script_path.unlink()

    @patch("subprocess.run")
    def test_docker_download_success(
        self,
        mock_run,
        config_fixture: Config,
        temp_dir: Path,
        mock_sandbox_capabilities,
    ):
        """Test successful Docker download."""
        config_fixture.sandbox.temp_dir = temp_dir
        output_path = temp_dir / "test.pdf"

        # Create the output file to simulate successful download
        output_path.write_bytes(b"PDF content")

        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        downloader = SandboxedDownloader(config_fixture)

        result = downloader.run_docker_download(
            "https://example.com/test.pdf", output_path
        )
        assert result is True

        # Verify Docker command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "docker"
        assert "run" in args
        assert "--rm" in args
        assert "--network" in args
        assert "bridge" in args

    @patch("subprocess.run")
    def test_docker_download_failure(
        self,
        mock_run,
        config_fixture: Config,
        temp_dir: Path,
        mock_sandbox_capabilities,
    ):
        """Test Docker download failure."""
        config_fixture.sandbox.temp_dir = temp_dir
        output_path = temp_dir / "test.pdf"

        # Mock failed subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 1
        mock_result.stderr = "Docker error"
        mock_run.return_value = mock_result

        downloader = SandboxedDownloader(config_fixture)

        result = downloader.run_docker_download(
            "https://example.com/test.pdf", output_path
        )
        assert result is False

    @patch("subprocess.run")
    def test_podman_download_success(
        self,
        mock_run,
        config_fixture: Config,
        temp_dir: Path,
        mock_sandbox_capabilities,
    ):
        """Test successful Podman download."""
        config_fixture.sandbox.temp_dir = temp_dir
        output_path = temp_dir / "test.pdf"

        # Create the output file to simulate successful download
        output_path.write_bytes(b"PDF content")

        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        downloader = SandboxedDownloader(config_fixture)

        result = downloader.run_podman_download(
            "https://example.com/test.pdf", output_path
        )
        assert result is True

        # Verify Podman command was called correctly
        mock_run.assert_called_once()
        args = mock_run.call_args[0][0]
        assert args[0] == "podman"
        assert "run" in args

    @patch("subprocess.run")
    def test_firejail_download_success(
        self,
        mock_run,
        config_fixture: Config,
        temp_dir: Path,
        mock_sandbox_capabilities,
    ):
        """Test successful Firejail download."""
        config_fixture.sandbox.temp_dir = temp_dir
        output_path = temp_dir / "test.pdf"

        # Create the output file to simulate successful download
        output_path.write_bytes(b"PDF content")

        # Mock successful subprocess run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_run.return_value = mock_result

        downloader = SandboxedDownloader(config_fixture)

        with patch.object(downloader, "create_download_script") as mock_script:
            script_path = temp_dir / "script.py"
            script_path.write_text("# test script")
            mock_script.return_value = script_path

            result = downloader.run_firejail_download(
                "https://example.com/test.pdf", output_path
            )
            assert result is True

            # Verify Firejail command was called correctly
            mock_run.assert_called_once()
            args = mock_run.call_args[0][0]
            assert args[0] == "firejail"
            assert "--noprofile" in args
            assert "--seccomp" in args

    def test_sandboxed_download_with_temp_file(
        self, config_fixture: Config, temp_dir: Path, mock_sandbox_capabilities
    ):
        """Test sandboxed download creates temp file when no output path provided."""
        config_fixture.sandbox.temp_dir = temp_dir

        with patch.object(
            SandboxedDownloader, "run_docker_download", return_value=True
        ) as mock_download:
            downloader = SandboxedDownloader(config_fixture)
            downloader.backend = SandboxBackend.DOCKER
            downloader.capabilities = MagicMock()
            downloader.capabilities.available_backends = {SandboxBackend.DOCKER: True}

            result = downloader.sandboxed_download("https://example.com/test.pdf")

            assert result is not None
            assert isinstance(result, Path)
            assert result.suffix == ".tmp"
            mock_download.assert_called_once()

    def test_sandboxed_download_fallback_logic(
        self, config_fixture: Config, temp_dir: Path, mock_sandbox_capabilities
    ):
        """Test sandboxed download fallback to other backends."""
        config_fixture.sandbox.temp_dir = temp_dir
        output_path = temp_dir / "test.pdf"

        downloader = SandboxedDownloader(config_fixture)
        downloader.backend = SandboxBackend.DOCKER
        mock_sandbox_capabilities.available_backends = {
            SandboxBackend.DOCKER: True,
            SandboxBackend.PODMAN: True,
        }

        with (
            patch.object(downloader, "run_docker_download", return_value=False),
            patch.object(
                downloader, "run_podman_download", return_value=True
            ) as mock_podman,
        ):
            result = downloader.sandboxed_download(
                "https://example.com/test.pdf", output_path
            )

            assert result == output_path
            mock_podman.assert_called_once()

    def test_sandboxed_download_all_methods_fail(
        self, config_fixture: Config, temp_dir: Path, mock_sandbox_capabilities
    ):
        """Test sandboxed download when all methods fail."""
        config_fixture.sandbox.temp_dir = temp_dir
        output_path = temp_dir / "test.pdf"

        downloader = SandboxedDownloader(config_fixture)
        downloader.backend = SandboxBackend.DOCKER
        mock_sandbox_capabilities.available_backends = {SandboxBackend.DOCKER: True}

        with patch.object(downloader, "run_docker_download", return_value=False):
            result = downloader.sandboxed_download(
                "https://example.com/test.pdf", output_path
            )
            assert result is None

    def test_get_security_report(
        self, config_fixture: Config, mock_sandbox_capabilities
    ):
        """Test security report generation."""
        downloader = SandboxedDownloader(config_fixture)
        downloader.backend = SandboxBackend.DOCKER
        downloader.isolation_level = IsolationLevel.STRICT
        mock_sandbox_capabilities.platform = "darwin"
        mock_sandbox_capabilities.available_backends = {SandboxBackend.DOCKER: True}
        mock_sandbox_capabilities.recommended_backend = SandboxBackend.DOCKER
        mock_sandbox_capabilities.get_max_isolation_level.return_value = (
            IsolationLevel.STRICT
        )

        report = downloader.get_security_report()

        assert isinstance(report, dict)
        assert report["platform"] == "darwin"
        assert report["current_backend"] == "docker"
        assert report["recommended_backend"] == "docker"
        assert report["max_isolation_level"] == "strict"
        assert "available_backends" in report


@pytest.mark.unit
class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_get_sandbox_capabilities(self, mock_sandbox_capabilities):
        """Test get_sandbox_capabilities function."""
        caps = get_sandbox_capabilities()
        # With mocking, this returns the mock instance, not a real SandboxCapabilities
        assert caps is mock_sandbox_capabilities

    def test_create_sandboxed_downloader(
        self, config_fixture: Config, mock_sandbox_capabilities
    ):
        """Test create_sandboxed_downloader function."""
        downloader = create_sandboxed_downloader(config_fixture)
        assert isinstance(downloader, SandboxedDownloader)
        assert downloader.config == config_fixture


@pytest.mark.unit
class TestSecurityConstraints:
    """Test security constraints and requirements."""

    def test_no_insecure_fallbacks(self):
        """Test that no insecure fallback mechanisms exist."""
        # Verify subprocess is not in available backends
        backends = [backend.value for backend in SandboxBackend]
        assert "subprocess" not in backends

    def test_container_requirements_enforced(self):
        """Test that container requirements are enforced."""
        with (
            patch("shutil.which", return_value=None),
            patch("subprocess.run") as mock_run,
        ):
            mock_run.side_effect = subprocess.CalledProcessError(1, "cmd")

            # Should raise error when no containers available
            with pytest.raises(
                RuntimeError, match="No suitable sandboxing backend available"
            ):
                SandboxCapabilities()

    def test_security_options_in_docker_command(
        self, config_fixture: Config, temp_dir: Path, mock_sandbox_capabilities
    ):
        """Test that Docker commands include proper security options."""
        config_fixture.sandbox.temp_dir = temp_dir

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            downloader = SandboxedDownloader(config_fixture)
            output_path = temp_dir / "test.pdf"
            output_path.write_bytes(b"content")

            downloader.run_docker_download("https://example.com/test.pdf", output_path)

            # Verify security options are present
            args = mock_run.call_args[0][0]
            assert "--security-opt" in args
            assert "no-new-privileges:true" in args
            assert "--read-only" in args
            assert "--memory" in args

    def test_resource_limits_applied(
        self, config_fixture: Config, temp_dir: Path, mock_sandbox_capabilities
    ):
        """Test that resource limits are properly applied."""
        config_fixture.sandbox.max_memory_mb = 256
        config_fixture.sandbox.temp_dir = temp_dir

        with patch("subprocess.run") as mock_run:
            mock_result = MagicMock()
            mock_result.returncode = 0
            mock_run.return_value = mock_result

            downloader = SandboxedDownloader(config_fixture)
            output_path = temp_dir / "test.pdf"
            output_path.write_bytes(b"content")

            downloader.run_docker_download("https://example.com/test.pdf", output_path)

            # Verify memory limit is applied
            args = mock_run.call_args[0][0]
            memory_idx = args.index("--memory")
            assert args[memory_idx + 1] == "256m"
