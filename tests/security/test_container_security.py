"""
Security tests for container isolation and sandboxing.

Tests Docker/Podman container security settings including privilege restrictions,
filesystem isolation, network controls, and container escape prevention.

OWASP References:
- A01:2021 - Broken Access Control
- A05:2021 - Security Misconfiguration
- A08:2021 - Software and Data Integrity Failures
- CWE-250: Execution with Unnecessary Privileges
- CWE-501: Trust Boundary Violation
"""

import pytest
import subprocess
import platform
from pathlib import Path
from unittest.mock import Mock, patch
from defuse.sandbox import (
    SandboxedDownloader,
    SandboxCapabilities,
    SandboxBackend,
    IsolationLevel,
)


@pytest.mark.security
class TestContainerSecurityOptions:
    """Test that containers are launched with proper security options."""

    def test_docker_no_new_privileges(self, config_fixture):
        """SECURITY: Docker containers must use --security-opt no-new-privileges."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            # Verify subprocess.run was called
            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify security option is present
            assert "--security-opt" in cmd
            no_priv_index = cmd.index("--security-opt")
            assert cmd[no_priv_index + 1] == "no-new-privileges:true"

    def test_docker_read_only_filesystem(self, config_fixture):
        """SECURITY: Docker containers must use --read-only filesystem."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --read-only flag is present
            assert "--read-only" in cmd

    def test_docker_tmpfs_noexec_nosuid(self, config_fixture):
        """SECURITY: Docker tmpfs must use noexec,nosuid flags."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Find --tmpfs option
            assert "--tmpfs" in cmd
            tmpfs_index = cmd.index("--tmpfs")
            tmpfs_value = cmd[tmpfs_index + 1]

            # Verify security flags
            assert "noexec" in tmpfs_value
            assert "nosuid" in tmpfs_value

    def test_podman_no_new_privileges(self, config_fixture):
        """SECURITY: Podman containers must use --security-opt no-new-privileges."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify security option is present
            assert "--security-opt" in cmd
            no_priv_index = cmd.index("--security-opt")
            assert cmd[no_priv_index + 1] == "no-new-privileges:true"

    def test_podman_read_only_filesystem(self, config_fixture):
        """SECURITY: Podman containers must use --read-only filesystem."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --read-only flag is present
            assert "--read-only" in cmd


@pytest.mark.security
class TestContainerResourceLimits:
    """Test that containers enforce resource limits."""

    def test_docker_memory_limit(self, config_fixture):
        """Docker containers must enforce memory limits."""
        # Set specific memory limit
        config_fixture.sandbox.max_memory_mb = 256
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --memory flag
            assert "--memory" in cmd
            memory_index = cmd.index("--memory")
            assert cmd[memory_index + 1] == "256m"

    def test_docker_cpu_limit(self, config_fixture):
        """Docker containers must enforce CPU limits."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --cpu-shares flag
            assert "--cpu-shares" in cmd
            cpu_index = cmd.index("--cpu-shares")
            # Should be a number (limited CPU shares)
            assert cmd[cpu_index + 1] == "512"

    def test_podman_memory_limit(self, config_fixture):
        """Podman containers must enforce memory limits."""
        config_fixture.sandbox.max_memory_mb = 512
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --memory flag
            assert "--memory" in cmd
            memory_index = cmd.index("--memory")
            assert cmd[memory_index + 1] == "512m"

    def test_podman_cpu_limit(self, config_fixture):
        """Podman containers must enforce CPU limits."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --cpus flag
            assert "--cpus" in cmd
            cpu_index = cmd.index("--cpus")
            # Should limit to 0.5 CPUs
            assert cmd[cpu_index + 1] == "0.5"


@pytest.mark.security
class TestContainerNetworkIsolation:
    """Test container network isolation settings."""

    def test_docker_network_mode(self, config_fixture):
        """Docker containers should use bridge network (isolated but allows downloads)."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --network flag
            assert "--network" in cmd
            network_index = cmd.index("--network")
            assert cmd[network_index + 1] == "bridge"

    def test_podman_network_mode(self, config_fixture):
        """Podman containers should use bridge network."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --network flag
            assert "--network" in cmd
            network_index = cmd.index("--network")
            assert cmd[network_index + 1] == "bridge"


@pytest.mark.security
class TestContainerCleanup:
    """Test that containers are properly cleaned up."""

    def test_docker_rm_flag(self, config_fixture):
        """Docker containers must use --rm flag for automatic cleanup."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --rm flag is present
            assert "--rm" in cmd

    def test_podman_rm_flag(self, config_fixture):
        """Podman containers must use --rm flag for automatic cleanup."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --rm flag is present
            assert "--rm" in cmd


@pytest.mark.security
class TestFirejailSandboxing:
    """Test Firejail sandbox security options."""

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Firejail only available on Linux"
    )
    def test_firejail_noroot_option(self, config_fixture):
        """SECURITY: Firejail must use --noroot option."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_firejail_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --noroot flag
            assert "--noroot" in cmd

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Firejail only available on Linux"
    )
    def test_firejail_seccomp_option(self, config_fixture):
        """SECURITY: Firejail must use --seccomp for syscall filtering."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_firejail_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --seccomp flag
            assert "--seccomp" in cmd

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Firejail only available on Linux"
    )
    def test_firejail_private_tmp(self, config_fixture):
        """SECURITY: Firejail must use --private-tmp for tmp isolation."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_firejail_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --private-tmp flag
            assert "--private-tmp" in cmd

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Firejail only available on Linux"
    )
    def test_firejail_resource_limits(self, config_fixture):
        """SECURITY: Firejail must set resource limits."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_firejail_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify resource limit flags
            assert any("--rlimit-fsize" in arg for arg in cmd)
            assert any("--rlimit-nofile" in arg for arg in cmd)
            assert any("--rlimit-nproc" in arg for arg in cmd)


@pytest.mark.security
class TestBubblewrapSandboxing:
    """Test Bubblewrap sandbox security options."""

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Bubblewrap only available on Linux"
    )
    def test_bubblewrap_new_session(self, config_fixture):
        """SECURITY: Bubblewrap must use --new-session."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_bubblewrap_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --new-session flag
            assert "--new-session" in cmd

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Bubblewrap only available on Linux"
    )
    def test_bubblewrap_die_with_parent(self, config_fixture):
        """SECURITY: Bubblewrap must use --die-with-parent."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_bubblewrap_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --die-with-parent flag
            assert "--die-with-parent" in cmd

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Bubblewrap only available on Linux"
    )
    def test_bubblewrap_unshare_pid(self, config_fixture):
        """SECURITY: Bubblewrap must use --unshare-pid for process isolation."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_bubblewrap_download(
                "https://example.com/file.pdf", output_path
            )

            assert mock_run.called
            cmd = mock_run.call_args[0][0]

            # Verify --unshare-pid flag
            assert "--unshare-pid" in cmd


@pytest.mark.security
class TestSandboxCapabilities:
    """Test sandbox capability detection."""

    def test_sandbox_detection_runs_safely(self):
        """Sandbox detection should not raise exceptions."""
        # Should not raise even if no sandbox tools are available
        capabilities = SandboxCapabilities()
        assert capabilities is not None
        assert capabilities.platform is not None
        assert isinstance(capabilities.available_backends, dict)

    def test_docker_availability_check(self):
        """Docker availability should be checked safely."""
        capabilities = SandboxCapabilities()

        # Should have a boolean result
        docker_available = capabilities.available_backends.get(
            SandboxBackend.DOCKER, False
        )
        assert isinstance(docker_available, bool)

    def test_podman_availability_check(self):
        """Podman availability should be checked safely."""
        capabilities = SandboxCapabilities()

        podman_available = capabilities.available_backends.get(
            SandboxBackend.PODMAN, False
        )
        assert isinstance(podman_available, bool)

    @pytest.mark.skipif(
        platform.system() != "Linux", reason="Linux sandbox tools only on Linux"
    )
    def test_linux_sandbox_tools_detection(self):
        """Linux-specific sandbox tools should only be detected on Linux."""
        capabilities = SandboxCapabilities()

        # Firejail and Bubblewrap should only be available on Linux
        assert SandboxBackend.FIREJAIL in capabilities.available_backends
        assert SandboxBackend.BUBBLEWRAP in capabilities.available_backends

    @pytest.mark.skipif(platform.system() == "Linux", reason="Non-Linux platforms only")
    def test_linux_sandbox_tools_not_on_other_platforms(self):
        """Linux-specific tools should not be available on other platforms."""
        capabilities = SandboxCapabilities()

        # Should be marked as unavailable
        assert capabilities.available_backends[SandboxBackend.FIREJAIL] is False
        assert capabilities.available_backends[SandboxBackend.BUBBLEWRAP] is False

    def test_recommended_backend_is_available(self):
        """Recommended backend should be one of the available backends."""
        capabilities = SandboxCapabilities()

        # If we have a recommended backend, it should be available
        if capabilities.recommended_backend != SandboxBackend.AUTO:
            assert (
                capabilities.available_backends[capabilities.recommended_backend]
                is True
            )

    def test_max_isolation_level_consistency(self):
        """Max isolation level should be consistent with available backends."""
        capabilities = SandboxCapabilities()
        max_level = capabilities.get_max_isolation_level()

        # Should be one of the defined levels
        assert max_level in [
            IsolationLevel.NONE,
            IsolationLevel.BASIC,
            IsolationLevel.STRICT,
            IsolationLevel.PARANOID,
        ]

        # If Linux sandbox tools available, should be PARANOID
        if capabilities.available_backends.get(
            SandboxBackend.FIREJAIL
        ) or capabilities.available_backends.get(SandboxBackend.BUBBLEWRAP):
            assert max_level == IsolationLevel.PARANOID

        # If container runtimes available, should be at least STRICT
        elif capabilities.available_backends.get(
            SandboxBackend.DOCKER
        ) or capabilities.available_backends.get(SandboxBackend.PODMAN):
            assert max_level == IsolationLevel.STRICT


@pytest.mark.security
class TestContainerTimeouts:
    """Test that containers enforce timeouts to prevent indefinite execution."""

    def test_docker_command_timeout(self, config_fixture):
        """Docker subprocess should have a timeout."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_docker_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            # Verify timeout parameter was passed
            call_kwargs = mock_run.call_args[1]
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"] == 150  # Should be 150 seconds

    def test_podman_command_timeout(self, config_fixture):
        """Podman subprocess should have a timeout."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            downloader.run_podman_download("https://example.com/file.pdf", output_path)

            assert mock_run.called
            call_kwargs = mock_run.call_args[1]
            assert "timeout" in call_kwargs
            assert call_kwargs["timeout"] == 150

    def test_timeout_prevents_indefinite_execution(self, config_fixture):
        """SECURITY: Timeout should prevent indefinite execution."""
        downloader = SandboxedDownloader(config_fixture)

        with patch("subprocess.run") as mock_run:
            # Simulate timeout
            mock_run.side_effect = subprocess.TimeoutExpired("docker", 150)

            output_path = Path("/tmp/test_output.pdf")
            output_path.parent.mkdir(parents=True, exist_ok=True)

            result = downloader.run_docker_download(
                "https://example.com/file.pdf", output_path
            )

            # Should return False on timeout, not raise exception
            assert result is False


@pytest.mark.security
class TestSecurityDocumentation:
    """Test that security expectations for containers are documented and met."""

    def test_all_container_backends_use_minimal_privileges(self, config_fixture):
        """SECURITY: All container backends must use minimal privileges."""
        downloader = SandboxedDownloader(config_fixture)

        backends_to_test = [
            (downloader.run_docker_download, "docker"),
            (downloader.run_podman_download, "podman"),
        ]

        for backend_func, backend_name in backends_to_test:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

                output_path = Path("/tmp/test_output.pdf")
                output_path.parent.mkdir(parents=True, exist_ok=True)

                backend_func("https://example.com/file.pdf", output_path)

                cmd = mock_run.call_args[0][0]

                # All backends must have security options
                assert "--security-opt" in cmd, (
                    f"{backend_name} must use --security-opt"
                )
                assert "--read-only" in cmd, f"{backend_name} must use --read-only"
                assert "--rm" in cmd, f"{backend_name} must use --rm for cleanup"

    def test_no_host_network_mode(self, config_fixture):
        """SECURITY: Containers must not use host network mode."""
        downloader = SandboxedDownloader(config_fixture)

        backends_to_test = [
            downloader.run_docker_download,
            downloader.run_podman_download,
        ]

        for backend_func in backends_to_test:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

                output_path = Path("/tmp/test_output.pdf")
                output_path.parent.mkdir(parents=True, exist_ok=True)

                backend_func("https://example.com/file.pdf", output_path)

                cmd = mock_run.call_args[0][0]
                cmd_str = " ".join(cmd)

                # Must not use --network host
                assert "--network host" not in cmd_str

    def test_no_privileged_containers(self, config_fixture):
        """SECURITY: Containers must not run in privileged mode."""
        downloader = SandboxedDownloader(config_fixture)

        backends_to_test = [
            downloader.run_docker_download,
            downloader.run_podman_download,
        ]

        for backend_func in backends_to_test:
            with patch("subprocess.run") as mock_run:
                mock_run.return_value = Mock(returncode=0, stderr="", stdout="SUCCESS")

                output_path = Path("/tmp/test_output.pdf")
                output_path.parent.mkdir(parents=True, exist_ok=True)

                backend_func("https://example.com/file.pdf", output_path)

                cmd = mock_run.call_args[0][0]

                # Must not use --privileged
                assert "--privileged" not in cmd
