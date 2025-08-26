"""
Shared pytest fixtures and test configuration.
"""

import io
import tempfile
from pathlib import Path
from typing import Generator, Dict, Any
from unittest.mock import MagicMock, patch

import pytest
from click.testing import CliRunner

from defuse.config import Config, SandboxConfig, SanitizerConfig


@pytest.fixture
def temp_dir() -> Generator[Path, None, None]:
    """Provide a temporary directory for tests."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        yield Path(tmp_dir)


@pytest.fixture
def config_fixture() -> Config:
    """Provide a test configuration object."""
    config = Config()
    config.sandbox = SandboxConfig()
    config.sanitizer = SanitizerConfig()
    config.verbose = False
    return config


@pytest.fixture
def sandbox_config_fixture() -> SandboxConfig:
    """Provide a test sandbox configuration."""
    return SandboxConfig(
        temp_dir=Path("/tmp/test-defuse"),
        max_file_size=50 * 1024 * 1024,  # 50MB for tests
        download_timeout=10,  # Shorter timeout for tests
        max_memory_mb=256,
        max_cpu_seconds=30,
        prefer_memory_download=True,
        isolation_level="strict",
        sandbox_backend="auto",
    )


@pytest.fixture
def sanitizer_config_fixture(temp_dir: Path) -> SanitizerConfig:
    """Provide a test sanitizer configuration."""
    return SanitizerConfig(
        output_dir=temp_dir / "output",
        keep_temp_files=False,
        ocr_lang=None,
        archive_original=False,
        keep_unsafe_files=False,
    )


@pytest.fixture
def cli_runner() -> CliRunner:
    """Provide a Click CLI test runner."""
    return CliRunner()


@pytest.fixture
def mock_docker():
    """Mock Docker client for integration tests."""
    with patch("docker.from_env") as mock_client:
        client = MagicMock()
        mock_client.return_value = client

        # Mock container operations
        container = MagicMock()
        container.wait.return_value = {"StatusCode": 0}
        container.logs.return_value = b"SUCCESS: Downloaded file"
        client.containers.run.return_value = container

        yield client


@pytest.fixture
def mock_dangerzone(temp_dir: Path):
    """Mock dangerzone-cli for sanitizer tests."""
    dangerzone_path = temp_dir / "dangerzone-cli"
    dangerzone_path.write_text("#!/bin/bash\necho 'Mock Dangerzone CLI'\n")
    dangerzone_path.chmod(0o755)

    with patch("subprocess.run") as mock_run:
        # Mock successful dangerzone run
        mock_result = MagicMock()
        mock_result.returncode = 0
        mock_result.stdout = "Document converted successfully"
        mock_result.stderr = ""
        mock_run.return_value = mock_result

        yield dangerzone_path


@pytest.fixture
def mock_sandbox_capabilities():
    """Mock SandboxCapabilities for testing."""
    from defuse.sandbox import SandboxBackend, IsolationLevel

    with patch("defuse.sandbox.SandboxCapabilities") as mock_caps_class:
        mock_caps = MagicMock()
        mock_caps.platform = "darwin"
        mock_caps.available_backends = {
            SandboxBackend.AUTO: True,
            SandboxBackend.DOCKER: True,
            SandboxBackend.PODMAN: False,
            SandboxBackend.FIREJAIL: False,
            SandboxBackend.BUBBLEWRAP: False,
        }
        mock_caps.recommended_backend = SandboxBackend.DOCKER
        mock_caps.get_max_isolation_level.return_value = IsolationLevel.STRICT

        mock_caps_class.return_value = mock_caps
        yield mock_caps


@pytest.fixture
def sample_pdf_data() -> bytes:
    """Provide sample PDF data for testing."""
    return b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF"


@pytest.fixture
def sample_docx_data() -> bytes:
    """Provide sample DOCX data for testing."""
    # Simplified ZIP structure that starts with ZIP magic bytes
    return b"PK\x03\x04\x14\x00\x00\x00\x08\x00[Content_Types].xml"


@pytest.fixture
def sample_png_data() -> bytes:
    """Provide sample PNG data for testing."""
    return b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$"


@pytest.fixture
def sample_formats_data() -> Dict[str, bytes]:
    """Provide sample data for various formats."""
    return {
        "pdf": b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF",
        "docx": b"PK\x03\x04\x14\x00\x00\x00\x08\x00[Content_Types].xml",
        "png": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$",
        "jpeg": b"\xff\xd8\xff\xe0\x00\x10JFIF\x00\x01\x01\x01\x00H\x00H\x00\x00\xff\xdb",
        "gif": b"GIF89a\x01\x00\x01\x00\x00\x00\x00!\xf9\x04\x01\x00\x00\x00\x00,",
        "rtf": b"{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}\\f0\\fs24 Hello World!}",
        "epub": b"PK\x03\x04\x14\x00\x00\x00\x08\x00mimetypeapplication/epub+zip",
    }


@pytest.fixture
def mock_http_responses():
    """Mock HTTP responses for download tests."""
    responses_data = {
        "pdf": {
            "content_type": "application/pdf",
            "data": b"%PDF-1.7\n1 0 obj\n<< /Type /Catalog /Pages 2 0 R >>\nendobj\n%%EOF",
        },
        "docx": {
            "content_type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            "data": b"PK\x03\x04\x14\x00\x00\x00\x08\x00[Content_Types].xml",
        },
        "png": {
            "content_type": "image/png",
            "data": b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$",
        },
    }
    return responses_data


@pytest.fixture
def temp_download_dir(temp_dir: Path) -> Path:
    """Provide a temporary directory for download tests."""
    download_dir = temp_dir / "downloads"
    download_dir.mkdir(exist_ok=True)
    return download_dir


@pytest.fixture(autouse=True)
def setup_test_environment(temp_dir: Path, monkeypatch):
    """Set up test environment variables and paths."""
    # Set test-specific environment variables
    monkeypatch.setenv("DEFUSE_TEST_MODE", "1")
    monkeypatch.setenv("DEFUSE_TEMP_DIR", str(temp_dir))

    # Mock system paths to use test directory
    test_config_dir = temp_dir / "config"
    test_config_dir.mkdir(exist_ok=True)

    # Patch config directory functions to use test directory
    with patch("defuse.cli.get_config_dir", return_value=test_config_dir):
        yield


# Test sample file generators
def create_test_file(file_path: Path, content: bytes) -> Path:
    """Create a test file with given content."""
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_bytes(content)
    return file_path


@pytest.fixture
def create_sample_files(temp_dir: Path, sample_formats_data: Dict[str, bytes]):
    """Create sample files for testing."""

    def _create_files(formats: list | None = None):
        if formats is None:
            formats = list(sample_formats_data.keys())

        files = {}
        for fmt in formats:
            if fmt in sample_formats_data:
                file_path = temp_dir / f"sample.{fmt}"
                create_test_file(file_path, sample_formats_data[fmt])
                files[fmt] = file_path
        return files

    return _create_files
