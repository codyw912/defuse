import io
import tempfile
import urllib.parse
import resource
from pathlib import Path
from typing import Optional, Union, BinaryIO
import requests
from tqdm import tqdm

from .config import SandboxConfig
from .formats import FileTypeDetector


class DocumentDownloadError(Exception):
    """Custom exception for document download errors"""

    pass


class SecureDocumentDownloader:
    """Secure document downloader with sandboxing and validation"""

    def __init__(self, config: SandboxConfig):
        self.config = config
        self.file_detector = FileTypeDetector()
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": config.user_agent,
                "Accept": "*/*",  # Accept all file types
            }
        )
        self._setup_resource_limits()

    def _setup_resource_limits(self):
        """Set up resource limits for the download process (Unix only)"""
        try:
            import platform

            if platform.system() == "Windows":
                # Resource limits not available on Windows
                return

            # Limit virtual memory to prevent memory exhaustion attacks
            max_memory = getattr(self.config, "max_memory_mb", 512) * 1024 * 1024
            resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))

            # Limit CPU time to prevent CPU exhaustion
            max_cpu_time = getattr(self.config, "max_cpu_seconds", 60)
            resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_time, max_cpu_time))

            # Limit number of file descriptors
            resource.setrlimit(resource.RLIMIT_NOFILE, (64, 128))

        except (OSError, ValueError, AttributeError):
            # Resource limits may fail on some systems, continue without them
            pass

    def validate_url(self, url: str) -> bool:
        """Validate URL format and domain restrictions"""
        try:
            parsed = urllib.parse.urlparse(url)

            if not all([parsed.scheme, parsed.netloc]):
                return False

            if parsed.scheme not in ["http", "https"]:
                return False

            if self.config.allowed_domains:
                domain = parsed.netloc.lower()
                if not any(
                    domain.endswith(allowed.lower())
                    for allowed in self.config.allowed_domains
                ):
                    return False

            return True
        except Exception:
            return False

    def check_content_type(self, response: requests.Response) -> bool:
        """Check if response content type indicates a supported document format"""
        content_type = response.headers.get("content-type", "").lower()
        if not content_type:
            # No content type - we'll validate by magic bytes later
            return True

        # Remove charset and other parameters
        mime_type = content_type.split(";")[0].strip()

        # Check if this MIME type is supported
        supported_formats = self.file_detector.detect_from_mime_type(mime_type)
        return len(supported_formats) > 0

    def validate_document_format(
        self, file_path: Path, expected_mime: Optional[str] = None
    ) -> bool:
        """Validate document format using magic bytes"""
        try:
            with open(file_path, "rb") as f:
                return self.file_detector.is_supported(
                    buffer=f, mime_type=expected_mime, filename=str(file_path)
                )
        except Exception:
            return False

    def validate_document_format_buffer(
        self,
        buffer: BinaryIO,
        expected_mime: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> bool:
        """Validate document format from buffer"""
        try:
            return self.file_detector.is_supported(
                buffer=buffer, mime_type=expected_mime, filename=filename
            )
        except Exception:
            return False

    def download_to_memory(
        self, url: str, max_memory_size: Optional[int] = None
    ) -> Union[io.BytesIO, tempfile.SpooledTemporaryFile]:
        """
        Download document to memory buffer with automatic spillover to disk

        Args:
            url: URL to download from
            max_memory_size: Max size to keep in memory (default: 10MB)

        Returns:
            BytesIO or SpooledTemporaryFile containing the download

        Raises:
            DocumentDownloadError: If download fails or validation fails
        """
        if not self.validate_url(url):
            raise DocumentDownloadError(f"Invalid or restricted URL: {url}")

        if max_memory_size is None:
            max_memory_size = (
                getattr(self.config, "max_memory_buffer_mb", 10) * 1024 * 1024
            )

        try:
            # Set up timeout alarm
            # Set up timeout (cross-platform via requests timeout parameter)

            # Get file info first
            response = self.session.head(url, timeout=self.config.download_timeout)
            response.raise_for_status()

            # Check content length
            content_length = int(response.headers.get("content-length", 0))
            if content_length > self.config.max_file_size:
                raise DocumentDownloadError(
                    f"File too large: {content_length} bytes "
                    f"(max: {self.config.max_file_size})"
                )

            # Choose memory strategy based on size
            if content_length > 0 and content_length <= max_memory_size:
                # Small file: use pure memory
                memory_buffer: Union[io.BytesIO, tempfile.SpooledTemporaryFile] = (
                    io.BytesIO()
                )
                use_buffer = memory_buffer
            else:
                # Large file or unknown size: use spooled temp file
                memory_buffer = tempfile.SpooledTemporaryFile(
                    max_size=max_memory_size, dir=str(self.config.temp_dir)
                )
                use_buffer = memory_buffer

            # Download with streaming
            response = self.session.get(
                url, timeout=self.config.download_timeout, stream=True
            )
            response.raise_for_status()

            # Verify content type
            content_type = response.headers.get("content-type", "")
            if not self.check_content_type(response):
                raise DocumentDownloadError(
                    f"Response content type '{content_type}' is not supported"
                )

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with tqdm(
                total=total_size, unit="B", unit_scale=True, desc="Downloading"
            ) as pbar:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        downloaded += len(chunk)
                        if downloaded > self.config.max_file_size:
                            # Timeout handled by requests
                            raise DocumentDownloadError(
                                "File size exceeded during download"
                            )

                        use_buffer.write(chunk)
                        pbar.update(len(chunk))

            # Reset position to start
            use_buffer.seek(0)

            # Validate document format
            if not self.validate_document_format_buffer(use_buffer, content_type):
                # Timeout handled by requests
                raise DocumentDownloadError(
                    "Downloaded file is not a supported document format"
                )

            # Timeout handled by requests  # Cancel timeout
            return use_buffer

        except requests.RequestException as e:
            # Timeout handled by requests
            raise DocumentDownloadError(f"Download failed: {str(e)}")
        except Exception as e:
            # Timeout handled by requests
            raise DocumentDownloadError(f"Unexpected error: {str(e)}")

    def save_buffer_to_file(
        self,
        buffer: Union[io.BytesIO, tempfile.SpooledTemporaryFile],
        output_path: Path,
    ) -> Path:
        """Save memory buffer to file"""
        try:
            buffer.seek(0)
            with open(output_path, "wb") as f:
                while True:
                    chunk = buffer.read(8192)
                    if not chunk:
                        break
                    f.write(chunk)
            return output_path
        except Exception as e:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            raise DocumentDownloadError(f"Failed to save buffer to file: {str(e)}")

    def download(
        self, url: str, output_path: Optional[Path] = None, prefer_memory: bool = True
    ) -> Path:
        """
        Download document from URL with security checks

        Args:
            url: URL to download from
            output_path: Optional output path, otherwise uses temp file
            prefer_memory: Use memory-first download strategy

        Returns:
            Path to downloaded file

        Raises:
            DocumentDownloadError: If download fails or validation fails
        """
        if prefer_memory:
            # Use memory-first download strategy
            memory_buffer = self.download_to_memory(url)

            # Prepare output path
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    dir=self.config.temp_dir, suffix=".tmp", delete=False
                )
                output_path = Path(temp_file.name)
                temp_file.close()

            # Save memory buffer to file
            return self.save_buffer_to_file(memory_buffer, output_path)

        else:
            # Fallback to direct file download (legacy method)
            return self._download_direct_to_file(url, output_path)

    def _download_direct_to_file(
        self, url: str, output_path: Optional[Path] = None
    ) -> Path:
        """Legacy direct-to-file download method (less secure)"""
        if not self.validate_url(url):
            raise DocumentDownloadError(f"Invalid or restricted URL: {url}")

        try:
            # Get file info first
            response = self.session.head(url, timeout=self.config.download_timeout)
            response.raise_for_status()

            # Check content length
            content_length = int(response.headers.get("content-length", 0))
            if content_length > self.config.max_file_size:
                raise DocumentDownloadError(
                    f"File too large: {content_length} bytes "
                    f"(max: {self.config.max_file_size})"
                )

            # Prepare output path
            if output_path is None:
                temp_file = tempfile.NamedTemporaryFile(
                    dir=self.config.temp_dir, suffix=".tmp", delete=False
                )
                output_path = Path(temp_file.name)
                temp_file.close()

            # Download with progress bar
            response = self.session.get(
                url, timeout=self.config.download_timeout, stream=True
            )
            response.raise_for_status()

            # Verify content type
            content_type = response.headers.get("content-type", "")
            if not self.check_content_type(response):
                raise DocumentDownloadError(
                    f"Response content type '{content_type}' is not supported"
                )

            total_size = int(response.headers.get("content-length", 0))
            downloaded = 0

            with open(output_path, "wb") as f:
                with tqdm(
                    total=total_size, unit="B", unit_scale=True, desc="Downloading"
                ) as pbar:
                    for chunk in response.iter_content(chunk_size=8192):
                        if chunk:
                            downloaded += len(chunk)
                            if downloaded > self.config.max_file_size:
                                output_path.unlink(missing_ok=True)
                                raise DocumentDownloadError(
                                    "File size exceeded during download"
                                )

                            f.write(chunk)
                            pbar.update(len(chunk))

            # Validate document format
            if not self.validate_document_format(output_path, content_type):
                output_path.unlink(missing_ok=True)
                raise DocumentDownloadError(
                    "Downloaded file is not a supported document format"
                )

            return output_path

        except requests.RequestException as e:
            if output_path and output_path.exists():
                output_path.unlink(missing_ok=True)
            raise DocumentDownloadError(f"Download failed: {str(e)}")
        except Exception as e:
            if output_path and output_path.exists():
                output_path.unlink(missing_ok=True)
            raise DocumentDownloadError(f"Unexpected error: {str(e)}")

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        try:
            # Clean up both .tmp files and any leftover document files
            for pattern in [
                "*.tmp",
                "*.pdf",
                "*.doc*",
                "*.xls*",
                "*.ppt*",
                "*.odt",
                "*.ods",
                "*.odp",
            ]:
                for temp_file in self.config.temp_dir.glob(pattern):
                    temp_file.unlink(missing_ok=True)
        except Exception:
            pass
