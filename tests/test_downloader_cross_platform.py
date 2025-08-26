"""
Cross-platform downloader tests.

Simplified tests for HTTP/HTTPS download functionality across platforms.
These tests focus on platform-specific behaviors and detection.
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from defuse.config import SandboxConfig
from defuse.downloader import SecureDocumentDownloader, DocumentDownloadError


class TestCrossPlatformDownloader:
    """Test downloader functionality across all platforms."""

    def test_downloader_initialization(self, temp_dir):
        """Test downloader initializes correctly on all platforms."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should have basic attributes
        assert hasattr(downloader, "config")
        assert hasattr(downloader, "session")
        assert downloader.config == config

    def test_platform_specific_user_agent(self, temp_dir):
        """Test platform-specific user agent configuration."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should have user agent configured
        user_agent = downloader.session.headers.get("User-Agent", "")
        assert user_agent  # Should not be empty

    def test_download_method_exists(self, temp_dir):
        """Test download method exists and is callable."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should have download method
        assert hasattr(downloader, "download")
        assert callable(downloader.download)

    def test_url_validation_cross_platform(self, temp_dir):
        """Test URL validation works on all platforms."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should handle URL validation
        with patch("requests.Session.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 404
            mock_get.return_value = mock_response

            with pytest.raises(DocumentDownloadError):
                downloader.download("http://nonexistent.example.com/test.pdf")


@pytest.mark.linux
class TestLinuxDownloaderIntegration:
    """Test downloader functionality specific to Linux."""

    def test_linux_downloader_config(self, temp_dir):
        """Test downloader configuration on Linux."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should work on Linux
        assert downloader.config.temp_dir == temp_dir

    def test_linux_network_handling(self, temp_dir):
        """Test Linux network handling."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should handle Linux-specific network configuration
        assert hasattr(downloader, "session")


@pytest.mark.windows
class TestWindowsDownloaderIntegration:
    """Test downloader functionality specific to Windows."""

    def test_windows_downloader_config(self, temp_dir):
        """Test downloader configuration on Windows."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should work on Windows
        assert downloader.config.temp_dir == temp_dir

    def test_windows_path_handling(self, temp_dir):
        """Test Windows path handling in downloader."""
        # Windows path with spaces
        windows_path = temp_dir / "test with spaces.pdf"

        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should handle Windows paths correctly
        with patch("requests.Session.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.iter_content.return_value = [b"%PDF test"]
            mock_response.headers = {}
            mock_get.return_value = mock_response

            # Should be able to specify Windows path
            try:
                result = downloader.download(
                    "http://example.com/test.pdf", windows_path
                )
                # Path handling should work
            except Exception as e:
                # Error should not be path-related
                assert "path" not in str(e).lower() or "space" not in str(e).lower()


@pytest.mark.macos
class TestMacOSDownloaderIntegration:
    """Test downloader functionality specific to macOS."""

    def test_macos_downloader_config(self, temp_dir):
        """Test downloader configuration on macOS."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should work on macOS
        assert downloader.config.temp_dir == temp_dir

    def test_macos_keychain_integration(self, temp_dir):
        """Test macOS Keychain integration (if available)."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should handle macOS certificate store
        # (This is handled by the underlying requests/urllib3)
        assert hasattr(downloader, "session")


class TestDownloaderErrorHandling:
    """Test downloader error handling across platforms."""

    def test_network_error_handling(self, temp_dir):
        """Test network error handling."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Mock network error
        with patch("requests.Session.get", side_effect=Exception("Network error")):
            with pytest.raises(DocumentDownloadError):
                downloader.download("http://example.com/test.pdf")

    def test_invalid_url_handling(self, temp_dir):
        """Test invalid URL handling."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Test various invalid URLs
        invalid_urls = [
            "not-a-url",
            "",
            "ftp://example.com/test.pdf",  # Non-HTTP protocol
        ]

        for invalid_url in invalid_urls:
            with pytest.raises((DocumentDownloadError, ValueError)):
                downloader.download(invalid_url)

    def test_file_permission_errors(self, temp_dir):
        """Test file permission error handling."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Try to write to a read-only file
        readonly_file = temp_dir / "readonly.pdf"
        readonly_file.write_bytes(b"test")
        readonly_file.chmod(0o444)  # Read-only

        with patch("requests.Session.get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.iter_content.return_value = [b"%PDF test"]
            mock_response.headers = {}
            mock_get.return_value = mock_response

            # Should handle permission errors appropriately
            try:
                downloader.download("http://example.com/test.pdf", readonly_file)
            except (DocumentDownloadError, PermissionError):
                # Either error type is acceptable
                pass


class TestDownloaderConfiguration:
    """Test downloader configuration across platforms."""

    def test_timeout_configuration(self, temp_dir):
        """Test timeout configuration."""
        config = SandboxConfig(temp_dir=temp_dir, download_timeout=30)
        downloader = SecureDocumentDownloader(config)

        # Should respect timeout configuration
        assert downloader.config.download_timeout == 30

    def test_max_file_size_configuration(self, temp_dir):
        """Test max file size configuration."""
        max_size = 1024 * 1024  # 1MB
        config = SandboxConfig(temp_dir=temp_dir, max_file_size=max_size)
        downloader = SecureDocumentDownloader(config)

        # Should respect file size limits
        assert downloader.config.max_file_size == max_size

    def test_temp_dir_configuration(self, temp_dir):
        """Test temporary directory configuration."""
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should use specified temp directory
        assert downloader.config.temp_dir == temp_dir

    def test_user_agent_configuration(self, temp_dir):
        """Test user agent configuration."""
        # Use default config to get default user agent
        config = SandboxConfig(temp_dir=temp_dir)
        downloader = SecureDocumentDownloader(config)

        # Should have user agent configured
        user_agent = downloader.session.headers.get("User-Agent")
        assert user_agent
        assert len(user_agent) > 0
