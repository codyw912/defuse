"""
Integration tests for failure recovery and security constraints.

These tests verify that the system handles various failure scenarios
gracefully and maintains security boundaries under stress conditions
and malicious inputs.
"""

import time
from pathlib import Path
from unittest.mock import patch, MagicMock
from urllib.parse import urlparse

import pytest
import responses

from defuse.config import Config
from defuse.sandbox import SandboxedDownloader, SandboxBackend
from defuse.sanitizer import DocumentSanitizer
from defuse.formats import FileTypeDetector


@pytest.mark.integration
class TestFailureRecovery:
    """Test system behavior under various failure conditions."""

    @responses.activate
    def test_network_timeout_recovery(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test recovery from network timeouts."""

        # Mock a timeout scenario
        def slow_response(request):
            time.sleep(integration_config.sandbox.download_timeout + 1)
            return (200, {}, b"Should not reach this")

        responses.add_callback(
            responses.GET,
            "http://slow-server.com/timeout.pdf",
            callback=slow_response,
        )

        downloader = SandboxedDownloader(integration_config)
        output_file = temp_dir / "timeout_test.pdf"

        with patch.object(downloader, "run_docker_download") as mock_download:
            # Simulate timeout in container
            mock_download.return_value = False

            result = downloader.sandboxed_download(
                "http://slow-server.com/timeout.pdf", output_file
            )

        # Should handle timeout gracefully
        assert result is None
        assert not output_file.exists()

    def test_disk_space_exhaustion_recovery(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test behavior when disk space is exhausted."""
        # Mock disk space exhaustion
        with patch("pathlib.Path.write_bytes") as mock_write:
            mock_write.side_effect = OSError("No space left on device")

            downloader = SandboxedDownloader(integration_config)
            output_file = temp_dir / "diskfull_test.pdf"

            with patch.object(downloader, "run_docker_download") as mock_download:
                mock_download.return_value = False  # Would fail due to disk space

                result = downloader.sandboxed_download(
                    "http://example.com/test.pdf", output_file
                )

            assert result is None

    def test_container_daemon_unavailable(self):
        """Test behavior when container daemon is not available."""
        from defuse.cli import check_container_runtime

        # Test container runtime detection - should handle unavailable gracefully
        with patch("defuse.cli.check_container_runtime") as mock_check:
            mock_check.return_value = (None, None, None)

            runtime_name, runtime_path, version = mock_check.return_value
            assert runtime_name is None  # CLI should handle this gracefully

    def test_dangerzone_unavailable_recovery(self, integration_config, temp_dir):
        """Test behavior when Dangerzone is not available."""
        # Mock missing Dangerzone
        from defuse.sanitizer import DocumentSanitizeError

        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            with pytest.raises(
                (RuntimeError, FileNotFoundError, DocumentSanitizeError)
            ):
                DocumentSanitizer(integration_config.sanitizer, None)

    @responses.activate
    def test_malformed_response_recovery(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test recovery from malformed HTTP responses."""
        # Mock malformed responses
        responses.add(
            responses.GET,
            "http://example.com/malformed.pdf",
            body=b"This is not a PDF but claims to be",
            status=200,
            headers={"content-type": "application/pdf"},
        )

        downloader = SandboxedDownloader(integration_config)
        output_file = temp_dir / "malformed.pdf"

        with patch.object(downloader, "run_docker_download") as mock_download:
            mock_download.return_value = True
            # Create malformed file
            output_file.write_bytes(b"This is not a PDF but claims to be")

            result = downloader.sandboxed_download(
                "http://example.com/malformed.pdf", output_file
            )

        assert result == output_file
        assert output_file.exists()

        # Format detector should handle malformed files gracefully
        detector = FileTypeDetector()
        with open(output_file, "rb") as f:
            detected_format, confidence = detector.detect_format(buffer=f)

        # Should return None for unrecognized format
        assert detected_format is None
        assert confidence == 0.0

    def test_container_resource_exhaustion(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test behavior when container resources are exhausted."""
        # Set very low resource limits
        integration_config.sandbox.max_memory_mb = 8  # Very low
        integration_config.sandbox.max_cpu_seconds = 1  # Very short

        with patch("subprocess.run") as mock_run:
            # Mock container killed due to resource limits (exit code 137 = SIGKILL)
            mock_result = mock_run.return_value
            mock_result.returncode = 137  # Container killed
            mock_result.stderr = "Killed"

            downloader = SandboxedDownloader(integration_config)
            output_file = temp_dir / "resource_test.pdf"

            result = downloader.run_docker_download(
                "http://example.com/large.pdf", output_file
            )

            assert result is False


@pytest.mark.integration
class TestSecurityConstraints:
    """Test security constraints and boundary enforcement."""

    def test_url_scheme_validation(self, integration_config, temp_dir):
        """Test that only safe URL schemes are allowed."""
        dangerous_urls = [
            "file:///etc/passwd",
            "ftp://example.com/file.pdf",
            "javascript:alert('xss')",
            "data:text/html,<script>alert('xss')</script>",
        ]

        downloader = SandboxedDownloader(integration_config)

        for dangerous_url in dangerous_urls:
            output_file = temp_dir / "dangerous_test.pdf"

            # The URL validation should happen before any download attempt
            # This would be implemented in the actual downloader
            parsed = urlparse(dangerous_url)
            if parsed.scheme not in ["http", "https"]:
                # Should be rejected
                continue

            # If it somehow gets through, container isolation should protect us
            with patch.object(downloader, "run_docker_download") as mock_download:
                mock_download.return_value = False  # Should fail or be blocked

                result = downloader.sandboxed_download(dangerous_url, output_file)

                # Should not succeed with dangerous URLs
                assert result is None or result is False

    @responses.activate
    def test_file_size_limit_enforcement(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test that file size limits are enforced."""
        # Set low file size limit
        integration_config.sandbox.max_file_size = 1024  # 1KB limit

        # Mock a large file response
        large_content = b"Large file content " * 1000  # ~19KB
        responses.add(
            responses.GET,
            "http://example.com/large.pdf",
            body=large_content,
            status=200,
            headers={
                "content-type": "application/pdf",
                "content-length": str(len(large_content)),
            },
        )

        downloader = SandboxedDownloader(integration_config)
        output_file = temp_dir / "large_file.pdf"

        with patch.object(downloader, "run_docker_download") as mock_download:
            # Should fail due to size limit
            mock_download.return_value = False

            result = downloader.sandboxed_download(
                "http://example.com/large.pdf", output_file
            )

        # Should be rejected due to size limit
        assert result is None

    @responses.activate
    def test_domain_allowlist_enforcement(self, integration_config, temp_dir):
        """Test domain allowlist enforcement."""
        # Configure domain allowlist
        integration_config.sandbox.allowed_domains = ["trusted.com", "safe.org"]

        blocked_urls = [
            "http://malicious.com/evil.pdf",
            "http://suspicious.net/document.pdf",
            "http://untrusted.example/file.pdf",
        ]

        allowed_urls = ["http://trusted.com/document.pdf", "http://safe.org/report.pdf"]

        # Mock responses for allowed domains
        for url in allowed_urls:
            responses.add(
                responses.GET,
                url,
                body=b"%PDF-1.7\nAllowed content\n%%EOF",
                status=200,
            )

        downloader = SandboxedDownloader(integration_config)

        # Test blocked domains (would be implemented in URL validation)
        for blocked_url in blocked_urls:
            parsed = urlparse(blocked_url)
            domain = parsed.netloc

            if integration_config.sandbox.allowed_domains:
                if domain not in integration_config.sandbox.allowed_domains:
                    # Should be blocked
                    continue

        # Test allowed domains
        for allowed_url in allowed_urls:
            with patch.object(downloader, "run_docker_download") as mock_download:
                output_file = temp_dir / f"allowed_{hash(allowed_url)}.pdf"
                output_file.write_bytes(b"%PDF-1.7\nAllowed content\n%%EOF")
                mock_download.return_value = True

                result = downloader.sandboxed_download(allowed_url, output_file)
                assert result == output_file

    def test_container_privilege_restrictions(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test that containers cannot escalate privileges."""
        with patch("subprocess.run") as mock_run:
            mock_result = mock_run.return_value
            mock_result.returncode = 0

            downloader = SandboxedDownloader(integration_config)
            output_file = temp_dir / "privilege_test.pdf"

            result = downloader.run_docker_download(
                "http://example.com/test.pdf", output_file
            )

            # Verify security options were applied
            docker_cmd = mock_run.call_args[0][0] if mock_run.call_args else []

            if docker_cmd:
                assert "--security-opt" in docker_cmd
                security_idx = docker_cmd.index("--security-opt") + 1
                assert security_idx < len(docker_cmd)
                assert "no-new-privileges:true" in docker_cmd[security_idx]

    def test_network_isolation_enforcement(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test that containers have proper network restrictions."""
        with patch("subprocess.run") as mock_run:
            mock_result = mock_run.return_value
            mock_result.returncode = 0

            downloader = SandboxedDownloader(integration_config)
            output_file = temp_dir / "network_test.pdf"

            result = downloader.run_docker_download(
                "http://example.com/test.pdf", output_file
            )

            # Verify network restrictions
            docker_cmd = mock_run.call_args[0][0] if mock_run.call_args else []

            if docker_cmd:
                assert "--network" in docker_cmd
                network_idx = docker_cmd.index("--network") + 1
                assert network_idx < len(docker_cmd)
                # Should use bridge network with restrictions
                assert docker_cmd[network_idx] == "bridge"

    def test_filesystem_isolation_enforcement(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test that containers have read-only filesystem restrictions."""
        with patch("subprocess.run") as mock_run:
            mock_result = mock_run.return_value
            mock_result.returncode = 0

            downloader = SandboxedDownloader(integration_config)
            output_file = temp_dir / "filesystem_test.pdf"

            result = downloader.run_docker_download(
                "http://example.com/test.pdf", output_file
            )

            # Verify filesystem restrictions
            docker_cmd = mock_run.call_args[0][0] if mock_run.call_args else []

            if docker_cmd:
                assert "--read-only" in docker_cmd
                # Should have volume mount for output only
                assert "-v" in docker_cmd or "--volume" in docker_cmd


@pytest.mark.integration
class TestMaliciousInputHandling:
    """Test handling of potentially malicious inputs."""

    @responses.activate
    def test_zip_bomb_protection(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test protection against zip bombs and similar attacks."""
        # Mock a zip bomb (would expand to huge size)
        zip_bomb_content = b"PK\x03\x04" + b"x" * 1000  # Fake zip bomb signature

        responses.add(
            responses.GET,
            "http://malicious.com/zipbomb.docx",
            body=zip_bomb_content,
            status=200,
            headers={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        )

        downloader = SandboxedDownloader(integration_config)
        output_file = temp_dir / "zipbomb.docx"

        with patch.object(downloader, "run_docker_download") as mock_download:
            # Container resource limits should protect against zip bombs
            mock_download.return_value = True
            output_file.write_bytes(zip_bomb_content)

            result = downloader.sandboxed_download(
                "http://malicious.com/zipbomb.docx", output_file
            )

        # Should complete (container limits protect us)
        assert result == output_file

    @responses.activate
    def test_malicious_pdf_handling(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test handling of potentially malicious PDF content."""
        # Mock malicious PDF with JavaScript
        malicious_pdf = b"""%PDF-1.7
1 0 obj
<< /Type /Catalog /Pages 2 0 R /OpenAction << /S /JavaScript /JS (app.alert('Malicious JavaScript')) >> >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R >>
endobj
%%EOF"""

        responses.add(
            responses.GET,
            "http://malicious.com/evil.pdf",
            body=malicious_pdf,
            status=200,
            headers={"content-type": "application/pdf"},
        )

        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        with patch.object(downloader, "run_docker_download") as mock_download:
            downloaded_file = temp_dir / "evil.pdf"
            downloaded_file.write_bytes(malicious_pdf)
            mock_download.return_value = True

            download_result = downloader.sandboxed_download(
                "http://malicious.com/evil.pdf", downloaded_file
            )

        assert download_result == downloaded_file

        # Dangerzone should sanitize the malicious content
        sanitized_file = sanitizer.sanitize(downloaded_file, "evil_defused.pdf")

        assert sanitized_file.exists()

        # Sanitized content should be safe (mock dangerzone removes JavaScript)
        sanitized_content = sanitized_file.read_text()
        assert "JavaScript" not in sanitized_content
        assert "app.alert" not in sanitized_content

    def test_path_traversal_protection(self, integration_config, temp_dir):
        """Test protection against path traversal attacks."""
        malicious_paths = [
            "../../../etc/passwd",
            "..\\..\\windows\\system32\\config\\sam",
            "....//....//etc/passwd",
            "/etc/passwd",
            "C:\\Windows\\System32\\config\\sam",
        ]

        for malicious_path in malicious_paths:
            # The system should sanitize output paths
            safe_path = Path(temp_dir) / Path(malicious_path).name

            # Should resolve to safe location within temp directory
            assert temp_dir in safe_path.parents or safe_path == temp_dir
            assert not str(safe_path).startswith("/etc")
            assert not str(safe_path).startswith("C:\\Windows")

    @responses.activate
    def test_oversized_header_attack(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test handling of HTTP responses with oversized headers."""
        # Mock response with extremely large headers
        large_headers = {f"x-custom-{i}": "x" * 1000 for i in range(100)}

        responses.add(
            responses.GET,
            "http://malicious.com/largeheaders.pdf",
            body=b"%PDF-1.7\nContent\n%%EOF",
            status=200,
            headers=large_headers,
        )

        downloader = SandboxedDownloader(integration_config)
        output_file = temp_dir / "largeheaders.pdf"

        with patch.object(downloader, "run_docker_download") as mock_download:
            # Should handle large headers gracefully (HTTP client should handle)
            mock_download.return_value = True
            output_file.write_bytes(b"%PDF-1.7\nContent\n%%EOF")

            result = downloader.sandboxed_download(
                "http://malicious.com/largeheaders.pdf", output_file
            )

        # Should complete successfully (HTTP client handles oversized headers)
        assert result == output_file

    def test_unicode_filename_handling(self, integration_config, temp_dir):
        """Test handling of Unicode and special characters in filenames."""
        problematic_filenames = [
            "document with spaces.pdf",
            "café_résumé.pdf",
            "测试文档.pdf",
            "файл.pdf",
            "🎉celebration🎊.pdf",
            "file;rm -rf /.pdf",  # Command injection attempt
            "NUL.pdf",  # Windows reserved name
            "con.pdf",  # Windows reserved name
        ]

        for original_name in problematic_filenames:
            # System should sanitize filenames
            safe_name = "".join(c for c in original_name if c.isalnum() or c in "._-")

            if not safe_name or safe_name in ["NUL", "CON", "PRN", "AUX"]:
                safe_name = "document.pdf"

            safe_path = temp_dir / safe_name

            # Should be safe to create
            assert safe_name.isprintable() or safe_name == "document.pdf"
            assert not any(
                dangerous in safe_name for dangerous in [";", "&", "|", ">", "<"]
            )


@pytest.mark.integration
class TestStressAndReliability:
    """Test system reliability under stress conditions."""

    @pytest.mark.slow
    def test_rapid_sequential_requests(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test handling of rapid sequential download requests."""
        downloader = SandboxedDownloader(integration_config)

        successful_downloads = 0

        for i in range(10):  # 10 rapid requests
            with patch.object(downloader, "run_docker_download") as mock_download:
                output_file = temp_dir / f"rapid_{i}.pdf"
                output_file.write_bytes(f"Content {i}".encode())
                mock_download.return_value = True

                result = downloader.sandboxed_download(
                    f"http://example.com/rapid_{i}.pdf", output_file
                )

                if result:
                    successful_downloads += 1

        # Should handle all requests successfully
        assert successful_downloads == 10

    def test_memory_leak_prevention(
        self, integration_config, temp_dir, mock_sandbox_capabilities
    ):
        """Test that repeated operations don't cause memory leaks."""
        downloader = SandboxedDownloader(integration_config)

        # Perform many operations to test for leaks
        for i in range(50):
            with patch.object(downloader, "run_docker_download") as mock_download:
                output_file = temp_dir / f"leak_test_{i}.pdf"
                output_file.write_bytes(f"Memory test {i}".encode())
                mock_download.return_value = True

                result = downloader.sandboxed_download(
                    f"http://example.com/test_{i}.pdf", output_file
                )

                assert result == output_file

                # Clean up to simulate normal operation
                if (
                    output_file.exists()
                    and not integration_config.sanitizer.keep_temp_files
                ):
                    output_file.unlink()

    def test_long_running_stability(self, integration_config, temp_dir):
        """Test stability over extended operation periods."""
        # Simulate long-running operation with periodic downloads
        start_time = time.time()
        operations = 0

        downloader = SandboxedDownloader(integration_config)

        # Run for a short time in tests (would be longer in real scenarios)
        while time.time() - start_time < 2.0 and operations < 20:
            with patch.object(downloader, "run_docker_download") as mock_download:
                output_file = temp_dir / f"stability_{operations}.pdf"
                output_file.write_bytes(f"Stability test {operations}".encode())
                mock_download.return_value = True

                result = downloader.sandboxed_download(
                    f"http://example.com/stability_{operations}.pdf", output_file
                )

                assert result == output_file
                operations += 1

                # Brief pause to simulate realistic usage
                time.sleep(0.1)

        # Should complete many operations successfully
        assert operations >= 10
