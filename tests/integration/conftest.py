"""
Shared fixtures and configuration for integration tests.

These fixtures provide controlled environments for testing the full
integration of Defuse components with external dependencies like
Docker, HTTP servers, and file systems.
"""

import http.server
import socketserver
import threading
import time
from pathlib import Path
from typing import Dict

import pytest
import responses

from defuse.config import Config, SandboxConfig, SanitizerConfig


@pytest.fixture
def integration_config(temp_dir: Path) -> Config:
    """Configuration optimized for integration testing."""
    config = Config()
    config.sandbox = SandboxConfig(
        temp_dir=temp_dir,
        max_file_size=50 * 1024 * 1024,  # 50MB for integration tests
        download_timeout=60,  # Reasonable timeout for integration
        max_memory_mb=256,  # Conservative memory limit
        max_cpu_seconds=60,  # Conservative CPU limit
        prefer_memory_download=False,  # Use files for integration tests
        isolation_level="strict",
        sandbox_backend="auto",
    )
    config.sanitizer = SanitizerConfig(
        output_dir=temp_dir / "output",
        keep_temp_files=True,  # Keep files for inspection during tests
        archive_original=False,
        keep_unsafe_files=False,
    )
    config.verbose = True  # Verbose output for debugging integration issues
    return config


@pytest.fixture
def sample_documents() -> Dict[str, bytes]:
    """Sample document contents for various formats."""
    return {
        "pdf": b"%PDF-1.7\\n1 0 obj\\n<< /Type /Catalog /Pages 2 0 R >>\\nendobj\\n%%EOF",
        "docx": b"PK\\x03\\x04\\x14\\x00\\x00\\x00\\x08\\x00[Content_Types].xml",
        "png": b"\\x89PNG\\r\\n\\x1a\\n\\x00\\x00\\x00\\rIHDR\\x00\\x00\\x00\\x01\\x00\\x00\\x00\\x01\\x01\\x00\\x00\\x00\\x007n\\xf9$",
        "jpeg": b"\\xff\\xd8\\xff\\xe0\\x00\\x10JFIF\\x00\\x01\\x01\\x01\\x00H\\x00H\\x00\\x00\\xff\\xdb",
        "rtf": b"{\\\\rtf1\\\\ansi\\\\deff0 {\\\\fonttbl {\\\\f0 Times New Roman;}}\\\\f0\\\\fs24 Test Document}",
        "large_pdf": b"%PDF-1.7\\n" + b"Large content " * 10000 + b"\\n%%EOF",
    }


@pytest.fixture
def mock_http_server():
    """
    Mock HTTP server fixture for controlled download testing.

    Provides a simple HTTP server that can serve various response scenarios
    for integration testing without relying on external services.
    """

    class MockHTTPHandler(http.server.BaseHTTPRequestHandler):
        def log_message(self, format, *args):
            # Suppress HTTP server logging during tests
            pass

        def do_GET(self):
            # Default response
            if self.path == "/test.pdf":
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", "100")
                self.end_headers()
                self.wfile.write(b"%PDF-1.7\\nTest PDF content\\n%%EOF" + b"\\x00" * 50)
            elif self.path == "/slow.pdf":
                # Simulate slow response
                time.sleep(2)
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.end_headers()
                self.wfile.write(b"%PDF-1.7\\nSlow PDF\\n%%EOF")
            elif self.path == "/large.pdf":
                # Large file for testing memory/size limits
                content = b"%PDF-1.7\\n" + b"Large content block " * 1000 + b"\\n%%EOF"
                self.send_response(200)
                self.send_header("Content-Type", "application/pdf")
                self.send_header("Content-Length", str(len(content)))
                self.end_headers()
                self.wfile.write(content)
            elif self.path == "/redirect":
                # Test redirect handling
                self.send_response(302)
                self.send_header("Location", "/test.pdf")
                self.end_headers()
            elif self.path == "/404":
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not Found")
            elif self.path == "/500":
                self.send_response(500)
                self.end_headers()
                self.wfile.write(b"Internal Server Error")
            else:
                self.send_response(404)
                self.end_headers()

    # Find a free port
    with socketserver.TCPServer(("localhost", 0), MockHTTPHandler) as httpd:
        port = httpd.server_address[1]

        # Start server in background thread
        server_thread = threading.Thread(target=httpd.serve_forever, daemon=True)
        server_thread.start()

        # Give server time to start
        time.sleep(0.1)

        yield f"http://localhost:{port}"

        httpd.shutdown()


@pytest.fixture
def mock_responses_server():
    """
    Alternative mock HTTP server using responses library.

    This provides more control over HTTP responses and is easier to configure
    for specific test scenarios.
    """
    with responses.RequestsMock() as rsps:
        # Default successful responses
        rsps.add(
            responses.GET,
            "http://example.com/test.pdf",
            body=b"%PDF-1.7\\nTest PDF content\\n%%EOF",
            status=200,
            headers={"content-type": "application/pdf", "content-length": "100"},
        )

        rsps.add(
            responses.GET,
            "http://example.com/large.pdf",
            body=b"%PDF-1.7\\n" + b"Large content " * 1000 + b"\\n%%EOF",
            status=200,
            headers={"content-type": "application/pdf"},
        )

        rsps.add(
            responses.GET,
            "http://example.com/error.pdf",
            json={"error": "Not found"},
            status=404,
        )

        rsps.add(
            responses.GET,
            "http://slow-server.com/test.pdf",
            body=b"%PDF-1.7\\nSlow server response\\n%%EOF",
            status=200,
        )

        # Malicious/test URLs
        rsps.add(
            responses.GET,
            "http://malicious.com/test.pdf",
            body=b"Potentially malicious content",
            status=200,
        )

        yield rsps


@pytest.fixture
def docker_available():
    """Check if Docker is available for testing."""
    try:
        import docker

        client = docker.from_env()
        client.ping()
        return True
    except Exception:
        return False


@pytest.fixture
def podman_available():
    """Check if Podman is available for testing."""
    import shutil

    return shutil.which("podman") is not None


@pytest.fixture
def container_runtime_available(docker_available, podman_available):
    """Skip test if no container runtime is available."""
    if not docker_available and not podman_available:
        pytest.skip("No container runtime (Docker/Podman) available")
    return docker_available or podman_available


@pytest.fixture
def mock_dangerzone_cli(temp_dir: Path):
    """Mock dangerzone-cli for cross-platform sanitization testing."""
    import os
    import shutil
    from unittest.mock import patch, MagicMock
    import platform

    # Check if we should use real Dangerzone instead of mocking
    if os.environ.get("DEFUSE_USE_REAL_DANGERZONE"):
        # Try to find real dangerzone-cli
        real_dangerzone = None

        # Look for dangerzone-cli in common locations
        possible_paths = [
            "dangerzone-cli",  # In PATH
            "C:\\Program Files\\Dangerzone\\dangerzone-cli.exe",  # Windows default
            "/usr/local/bin/dangerzone-cli",  # macOS/Linux common
            "/usr/bin/dangerzone-cli",  # Linux common
        ]

        for path_candidate in possible_paths:
            if shutil.which(path_candidate) or Path(path_candidate).exists():
                real_dangerzone = Path(path_candidate)
                print(f"✅ Using REAL Dangerzone at: {real_dangerzone}")
                yield real_dangerzone
                return

        print(
            "⚠️ DEFUSE_USE_REAL_DANGERZONE set but Dangerzone not found, falling back to mock"
        )

    dangerzone_path = temp_dir / "mock-dangerzone-cli"

    # Create platform-appropriate mock executable
    if platform.system() == "Windows":
        # Create a Windows batch file
        mock_script = """@echo off
echo Mock Dangerzone: Converting %1 to %2
echo %%PDF-1.7 > %2
echo Mock sanitized document >> %2
echo %%%%EOF >> %2
"""
        dangerzone_path = dangerzone_path.with_suffix(".bat")
        dangerzone_path.write_text(mock_script)
    else:
        # Create a Unix shell script
        mock_script = """#!/bin/bash
echo "Mock Dangerzone: Converting $1 to $2"
printf "%%PDF-1.7\\nMock sanitized document\\n%%%%EOF" > "$2"
"""
        dangerzone_path.write_text(mock_script)
        dangerzone_path.chmod(0o755)

    # Also mock subprocess.run to ensure consistent behavior across platforms
    with patch("subprocess.run") as mock_run:

        def mock_dangerzone_call(cmd, *args, **kwargs):
            # Extract output filename from command
            if "--output-filename" in cmd:
                idx = cmd.index("--output-filename")
                if idx + 1 < len(cmd):
                    output_file = kwargs.get("cwd", temp_dir) / cmd[idx + 1]
                    # Create mock sanitized PDF with proper structure and size
                    # Must be >= 100 bytes and start with %PDF for validation
                    output_content = b"""%PDF-1.7
1 0 obj
<< /Type /Catalog /Pages 2 0 R >>
endobj
2 0 obj
<< /Type /Pages /Kids [3 0 R] /Count 1 >>
endobj
3 0 obj
<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] >>
endobj
xref
0 4
0000000000 65535 f
0000000010 00000 n
0000000079 00000 n
0000000173 00000 n
trailer
<< /Size 4 /Root 1 0 R >>
startxref
456
%%EOF"""
                    Path(output_file).write_bytes(output_content)

            # Return successful result
            result = MagicMock()
            result.returncode = 0
            result.stdout = "Mock Dangerzone: Document converted successfully"
            result.stderr = ""
            return result

        mock_run.side_effect = mock_dangerzone_call
        yield dangerzone_path


@pytest.fixture
def test_urls_file(temp_dir: Path, sample_documents: Dict[str, bytes]):
    """Create a test URLs file for batch processing tests."""
    urls_file = temp_dir / "test_urls.txt"
    urls_content = """# Test URLs file for batch processing
http://example.com/document1.pdf
http://example.com/document2.docx
http://example.com/image1.png
http://slow-server.com/large.pdf

# This is a comment and should be ignored
http://example.com/final.pdf"""

    urls_file.write_text(urls_content)
    return urls_file


@pytest.fixture(autouse=True)
def integration_test_environment(temp_dir: Path, monkeypatch):
    """Set up environment for integration tests."""
    # Set test-specific environment variables
    monkeypatch.setenv("DEFUSE_TEST_MODE", "integration")
    monkeypatch.setenv("DEFUSE_TEMP_DIR", str(temp_dir))

    # Ensure output directories exist
    output_dir = temp_dir / "output"
    output_dir.mkdir(exist_ok=True)

    sandbox_temp = temp_dir / "sandbox"
    sandbox_temp.mkdir(exist_ok=True)

    yield

    # Cleanup is handled by temp_dir fixture


@pytest.fixture
def large_file_content():
    """Generate large file content for testing file size limits."""
    # Generate ~10MB of content
    chunk = b"This is a test chunk of data for file size limit testing. " * 1000
    return chunk * 200  # Approximately 10MB


@pytest.fixture
def network_timeout_simulation():
    """Simulate various network timeout scenarios."""

    def _simulate_timeout(timeout_type="slow"):
        if timeout_type == "slow":
            time.sleep(5)  # Simulate slow response
        elif timeout_type == "hang":
            time.sleep(300)  # Simulate hanging connection
        elif timeout_type == "interrupt":
            raise ConnectionError("Simulated network interruption")

    return _simulate_timeout


# Skip markers for integration tests
def pytest_configure(config):
    """Configure custom markers for integration tests."""
    config.addinivalue_line(
        "markers",
        "integration: mark test as integration test requiring external resources",
    )
    config.addinivalue_line("markers", "docker: mark test as requiring Docker")
    config.addinivalue_line("markers", "podman: mark test as requiring Podman")
    config.addinivalue_line("markers", "slow: mark test as slow running")
    config.addinivalue_line("markers", "network: mark test as requiring network access")
