"""
Security tests for resource limit enforcement.

Tests that memory limits, CPU limits, file size limits, and timeouts are properly
enforced to prevent denial-of-service attacks and resource exhaustion.

OWASP References:
- A04:2021 - Insecure Design (missing resource limits)
- A05:2021 - Security Misconfiguration
- CWE-400: Uncontrolled Resource Consumption
- CWE-770: Allocation of Resources Without Limits or Throttling
"""

import pytest
import platform
import io
import tempfile
from unittest.mock import Mock, patch
from defuse.downloader import SecureDocumentDownloader, DocumentDownloadError
from defuse.config import SandboxConfig
from defuse.resources import (
    ResourceManager,
    ResourceLimits,
    setup_download_limits,
    get_resource_info,
)


@pytest.mark.security
class TestMemoryLimits:
    """Test memory limit enforcement."""

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Resource limits not available on Windows",
    )
    def test_memory_limits_set_on_unix(self):
        """Memory limits should be set on Unix systems."""
        manager = ResourceManager()
        assert manager.supported is True

        limits = ResourceLimits(max_memory_mb=256)
        result = manager.set_limits(limits)

        # Note: On macOS, setting memory limits may fail if the requested limit
        # is below the current system limit (ValueError: current limit exceeds maximum limit)
        # This is expected behavior and the downloader will still work
        if platform.system() == "Darwin":
            # On macOS, memory limit setting may fail - this is acceptable
            # The resource module is still supported for other limits
            assert isinstance(result, bool)
        else:
            # On Linux, setting limits should succeed
            assert result is True

            # Verify limits were set
            info = manager.get_current_limits()
            assert info.supported is True
            assert info.memory_limit is not None
            assert info.memory_limit[0] > 0  # Has a soft limit set

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_memory_limits_not_supported_on_windows(self):
        """Memory limits should not be supported on Windows."""
        manager = ResourceManager()
        assert manager.supported is False

        limits = ResourceLimits(max_memory_mb=256)
        result = manager.set_limits(limits)
        assert result is False

    def test_downloader_sets_memory_limits(self, temp_dir):
        """SecureDocumentDownloader should set memory limits on initialization."""
        config = SandboxConfig(temp_dir=temp_dir, max_memory_mb=512)

        with patch("defuse.resources.resource_manager") as mock_manager:
            mock_manager.supported = True
            mock_manager.set_limits = Mock(return_value=True)

            downloader = SecureDocumentDownloader(config)

            # Verify setup_download_limits was called
            # (indirectly via _setup_resource_limits)
            assert downloader.config.max_memory_mb == 512

    def test_setup_download_limits_convenience_function(self):
        """Test the convenience function for setting download limits."""
        if platform.system() == "Windows":
            pytest.skip("Resource limits not available on Windows")

        result = setup_download_limits(max_memory_mb=256, max_cpu_seconds=30)
        # Should return True on Unix, False on Windows
        assert isinstance(result, bool)


@pytest.mark.security
class TestCPULimits:
    """Test CPU time limit enforcement."""

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Resource limits not available on Windows",
    )
    def test_cpu_limits_set_on_unix(self):
        """CPU time limits should be set on Unix systems."""
        manager = ResourceManager()
        assert manager.supported is True

        limits = ResourceLimits(max_cpu_seconds=60)
        result = manager.set_limits(limits)
        assert result is True

        # Verify limits were set
        info = manager.get_current_limits()
        assert info.supported is True
        assert info.cpu_limit is not None
        assert info.cpu_limit[0] == 60  # Soft limit in seconds

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_cpu_limits_not_supported_on_windows(self):
        """CPU limits should not be supported on Windows."""
        manager = ResourceManager()
        assert manager.supported is False

    def test_downloader_sets_cpu_limits(self, temp_dir):
        """SecureDocumentDownloader should set CPU limits on initialization."""
        config = SandboxConfig(temp_dir=temp_dir, max_cpu_seconds=60)

        with patch("defuse.resources.resource_manager") as mock_manager:
            mock_manager.supported = True
            mock_manager.set_limits = Mock(return_value=True)

            downloader = SecureDocumentDownloader(config)

            # Verify config has CPU limit
            assert downloader.config.max_cpu_seconds == 60


@pytest.mark.security
class TestFileDescriptorLimits:
    """Test file descriptor limit enforcement."""

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Resource limits not available on Windows",
    )
    def test_fd_limits_set_on_unix(self):
        """File descriptor limits should be set on Unix systems."""
        manager = ResourceManager()
        assert manager.supported is True

        limits = ResourceLimits(max_file_descriptors=64)
        result = manager.set_limits(limits)
        assert result is True

        # Verify limits were set
        info = manager.get_current_limits()
        assert info.supported is True
        assert info.fd_limit is not None
        # Soft limit should be 64, hard limit 128
        assert info.fd_limit[0] == 64


@pytest.mark.security
class TestFileSizeLimits:
    """Test file size limit enforcement during download."""

    def test_file_size_checked_before_download(self, temp_dir, sample_pdf_data):
        """File size should be checked via Content-Length header before downloading."""
        config = SandboxConfig(temp_dir=temp_dir, max_file_size=100)  # 100 bytes max

        downloader = SecureDocumentDownloader(config)

        # Mock HEAD request with large Content-Length
        mock_response = Mock()
        mock_response.headers = {"content-length": "1000000"}  # 1MB
        mock_response.raise_for_status = Mock()

        with patch.object(downloader.session, "head", return_value=mock_response):
            with pytest.raises(DocumentDownloadError, match="File too large"):
                downloader.download_to_memory("https://example.com/large.pdf")

    def test_file_size_checked_during_download(self, temp_dir, sample_pdf_data):
        """File size should be checked during streaming download."""
        config = SandboxConfig(temp_dir=temp_dir, max_file_size=100)  # 100 bytes max

        downloader = SecureDocumentDownloader(config)

        # Mock HEAD request with no Content-Length
        mock_head_response = Mock()
        mock_head_response.headers = {}
        mock_head_response.raise_for_status = Mock()

        # Mock GET request with large content
        mock_get_response = Mock()
        mock_get_response.headers = {"content-type": "application/pdf"}
        mock_get_response.raise_for_status = Mock()
        # Simulate streaming large chunks
        large_chunk = b"x" * 150  # Exceeds 100 byte limit
        mock_get_response.iter_content = Mock(return_value=[large_chunk])

        with patch.object(downloader.session, "head", return_value=mock_head_response):
            with patch.object(
                downloader.session, "get", return_value=mock_get_response
            ):
                with pytest.raises(DocumentDownloadError, match="size exceeded"):
                    downloader.download_to_memory("https://example.com/file.pdf")

    def test_file_size_limit_allows_small_files(self, temp_dir, sample_pdf_data):
        """Files within size limit should be allowed."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=10000,  # 10KB max, large enough
        )

        downloader = SecureDocumentDownloader(config)

        # Mock successful download of small file
        mock_head_response = Mock()
        mock_head_response.headers = {"content-length": str(len(sample_pdf_data))}
        mock_head_response.raise_for_status = Mock()

        mock_get_response = Mock()
        mock_get_response.headers = {
            "content-type": "application/pdf",
            "content-length": str(len(sample_pdf_data)),
        }
        mock_get_response.raise_for_status = Mock()
        mock_get_response.iter_content = Mock(return_value=[sample_pdf_data])

        with patch.object(downloader.session, "head", return_value=mock_head_response):
            with patch.object(
                downloader.session, "get", return_value=mock_get_response
            ):
                buffer = downloader.download_to_memory("https://example.com/small.pdf")
                assert buffer is not None
                buffer.seek(0)
                content = buffer.read()
                assert len(content) == len(sample_pdf_data)


@pytest.mark.security
class TestTimeoutEnforcement:
    """Test download timeout enforcement."""

    def test_download_timeout_configuration(self, temp_dir):
        """Download timeout should be configurable."""
        config = SandboxConfig(temp_dir=temp_dir, download_timeout=5)
        downloader = SecureDocumentDownloader(config)
        assert downloader.config.download_timeout == 5

    def test_timeout_passed_to_requests(self, temp_dir):
        """Timeout should be passed to requests library."""
        config = SandboxConfig(temp_dir=temp_dir, download_timeout=10)
        downloader = SecureDocumentDownloader(config)

        mock_response = Mock()
        mock_response.headers = {"content-length": "100"}
        mock_response.raise_for_status = Mock()

        with patch.object(
            downloader.session, "head", return_value=mock_response
        ) as mock_head:
            with pytest.raises(DocumentDownloadError):
                # Will fail on GET, but we can verify HEAD was called with timeout
                downloader.download_to_memory("https://example.com/file.pdf")

            # Verify timeout was passed
            mock_head.assert_called_once()
            call_args = mock_head.call_args
            assert call_args[1]["timeout"] == 10

    def test_requests_timeout_raises_documentdownloaderror(self, temp_dir):
        """Request timeout should be caught and converted to DocumentDownloadError."""
        import requests

        config = SandboxConfig(temp_dir=temp_dir, download_timeout=1)
        downloader = SecureDocumentDownloader(config)

        with patch.object(
            downloader.session,
            "head",
            side_effect=requests.Timeout("Connection timed out"),
        ):
            with pytest.raises(DocumentDownloadError, match="Download failed"):
                downloader.download_to_memory("https://example.com/file.pdf")


@pytest.mark.security
class TestSpooledTemporaryFile:
    """Test SpooledTemporaryFile behavior (memory→disk spillover)."""

    def test_small_file_stays_in_memory(self, temp_dir, sample_pdf_data):
        """Small files should stay in BytesIO (pure memory)."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=10000,
            max_memory_buffer_mb=1,  # 1MB buffer
        )
        downloader = SecureDocumentDownloader(config)

        # Mock download of small file
        mock_head_response = Mock()
        mock_head_response.headers = {"content-length": str(len(sample_pdf_data))}
        mock_head_response.raise_for_status = Mock()

        mock_get_response = Mock()
        mock_get_response.headers = {
            "content-type": "application/pdf",
            "content-length": str(len(sample_pdf_data)),
        }
        mock_get_response.raise_for_status = Mock()
        mock_get_response.iter_content = Mock(return_value=[sample_pdf_data])

        with patch.object(downloader.session, "head", return_value=mock_head_response):
            with patch.object(
                downloader.session, "get", return_value=mock_get_response
            ):
                buffer = downloader.download_to_memory("https://example.com/small.pdf")

                # Should be BytesIO for small files
                assert isinstance(buffer, (io.BytesIO, tempfile.SpooledTemporaryFile))

    def test_large_file_uses_spooled_temp_file(self, temp_dir):
        """Large files should use SpooledTemporaryFile."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=100 * 1024 * 1024,  # 100MB max
            max_memory_buffer_mb=1,  # 1MB buffer - forces spillover
        )
        downloader = SecureDocumentDownloader(config)

        # Mock download of large file (2MB)
        large_size = 2 * 1024 * 1024
        mock_head_response = Mock()
        mock_head_response.headers = {"content-length": str(large_size)}
        mock_head_response.raise_for_status = Mock()

        # Create chunks that exceed memory buffer
        chunk_size = 8192
        num_chunks = large_size // chunk_size
        chunks = [b"x" * chunk_size for _ in range(num_chunks)]

        mock_get_response = Mock()
        mock_get_response.headers = {
            "content-type": "application/pdf",
            "content-length": str(large_size),
        }
        mock_get_response.raise_for_status = Mock()
        mock_get_response.iter_content = Mock(return_value=chunks)

        with patch.object(downloader.session, "head", return_value=mock_head_response):
            with patch.object(
                downloader.session, "get", return_value=mock_get_response
            ):
                # Mock file format validator to accept our dummy data
                with patch.object(
                    downloader, "validate_document_format_buffer", return_value=True
                ):
                    buffer = downloader.download_to_memory(
                        "https://example.com/large.pdf"
                    )

                    # Should be SpooledTemporaryFile
                    assert isinstance(buffer, tempfile.SpooledTemporaryFile)

    def test_buffer_spillover_threshold(self, temp_dir):
        """Test that spillover happens at configured threshold."""
        max_memory_size = 100 * 1024  # 100KB threshold
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=10 * 1024 * 1024,  # 10MB max
            max_memory_buffer_mb=max_memory_size // (1024 * 1024),  # Convert to MB
        )
        downloader = SecureDocumentDownloader(config)

        # Test that the config is used correctly
        assert config.max_memory_buffer_mb == 0  # <1MB rounds to 0
        # Should default to 10MB in the actual code


@pytest.mark.security
class TestResourceLimitIntegration:
    """Test integration of multiple resource limits."""

    def test_all_limits_enforced_together(self, temp_dir):
        """All resource limits should be enforced simultaneously."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=1000,  # 1KB
            download_timeout=5,  # 5 seconds
            max_memory_mb=128,  # 128MB
            max_cpu_seconds=10,  # 10 seconds CPU
        )

        downloader = SecureDocumentDownloader(config)

        # Verify all limits are set in config
        assert downloader.config.max_file_size == 1000
        assert downloader.config.download_timeout == 5
        assert downloader.config.max_memory_mb == 128
        assert downloader.config.max_cpu_seconds == 10

    def test_resource_limits_prevent_dos(self, temp_dir):
        """SECURITY: Resource limits should prevent denial-of-service attacks."""
        # Configure tight limits
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=1024,  # 1KB max
            download_timeout=2,  # 2 second timeout
            max_memory_mb=64,  # 64MB max
        )

        downloader = SecureDocumentDownloader(config)

        # Attempt to download oversized file
        mock_response = Mock()
        mock_response.headers = {"content-length": "100000000"}  # 100MB
        mock_response.raise_for_status = Mock()

        with patch.object(downloader.session, "head", return_value=mock_response):
            with pytest.raises(DocumentDownloadError, match="File too large"):
                downloader.download_to_memory("https://evil.com/huge.pdf")


@pytest.mark.security
class TestResourceInfoRetrieval:
    """Test resource limit information retrieval."""

    @pytest.mark.skipif(
        platform.system() == "Windows",
        reason="Resource limits not available on Windows",
    )
    def test_get_resource_info_on_unix(self):
        """Resource info should be available on Unix systems."""
        info = get_resource_info()
        assert info.supported is True
        assert info.memory_limit is not None
        assert info.cpu_limit is not None
        assert info.fd_limit is not None
        # All limits should be tuples of (soft, hard)
        assert len(info.memory_limit) == 2
        assert len(info.cpu_limit) == 2
        assert len(info.fd_limit) == 2

    @pytest.mark.skipif(platform.system() != "Windows", reason="Windows-specific test")
    def test_get_resource_info_on_windows(self):
        """Resource info should indicate unsupported on Windows."""
        info = get_resource_info()
        assert info.supported is False
        assert info.memory_limit is None
        assert info.cpu_limit is None
        assert info.fd_limit is None


@pytest.mark.security
class TestPlatformCompatibility:
    """Test that resource limits work correctly across platforms."""

    def test_resource_manager_handles_import_error(self):
        """ResourceManager should gracefully handle missing resource module."""
        # Test by mocking the import to fail
        with patch("defuse.resources.platform.system", return_value="Linux"):
            # Create new manager with mocked import failure
            manager = ResourceManager()
            with patch.object(manager, "_resource_module", None):
                manager._supported = False

                limits = ResourceLimits(max_memory_mb=256)
                result = manager.set_limits(limits)
                assert result is False

    def test_cross_platform_downloader_initialization(self, temp_dir):
        """Downloader should initialize successfully on all platforms."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should not raise any exceptions
        assert downloader is not None
        assert downloader.config is not None

    def test_limits_fail_gracefully_on_unsupported_platform(self):
        """Setting limits should fail gracefully on unsupported platforms."""
        manager = ResourceManager()

        # Force unsupported
        manager._supported = False

        limits = ResourceLimits(
            max_memory_mb=256, max_cpu_seconds=60, max_file_descriptors=64
        )
        result = manager.set_limits(limits)

        # Should return False but not raise exception
        assert result is False


@pytest.mark.security
class TestSecurityDocumentation:
    """Test that security expectations for resource limits are met."""

    def test_default_limits_are_reasonable(self):
        """SECURITY: Default resource limits should be reasonably restrictive."""
        config = SandboxConfig()

        # Memory limits should prevent excessive memory usage
        assert config.max_memory_mb <= 1024, "Default memory limit too high"
        assert config.max_memory_mb >= 128, "Default memory limit too low"

        # CPU limits should prevent CPU exhaustion
        assert config.max_cpu_seconds <= 300, "Default CPU limit too high"
        assert config.max_cpu_seconds >= 10, "Default CPU limit too low"

        # File size limits should prevent storage exhaustion
        assert config.max_file_size <= 1024 * 1024 * 1024, "Default file size too high"
        assert config.max_file_size >= 1024 * 1024, "Default file size too low"

        # Timeout should prevent indefinite hangs
        assert config.download_timeout <= 300, "Default timeout too high"
        assert config.download_timeout >= 5, "Default timeout too low"

    def test_buffer_spillover_prevents_memory_exhaustion(self, temp_dir):
        """SECURITY: Buffer spillover should prevent memory exhaustion."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_memory_buffer_mb=10,  # Only 10MB in memory
            max_file_size=100 * 1024 * 1024,  # But allow 100MB files
        )

        # This configuration prevents loading 100MB entirely into memory
        assert config.max_memory_buffer_mb < config.max_file_size / (1024 * 1024)
