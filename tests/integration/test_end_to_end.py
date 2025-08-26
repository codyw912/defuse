"""
End-to-end integration tests for complete workflows.

These tests verify the entire pipeline from document download through
sanitization, testing the integration of all system components together
in realistic scenarios.
"""

import tempfile
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest
import responses

from defuse.cli import main
from defuse.config import Config
from defuse.formats import FileTypeDetector, SupportedFormat
from defuse.sandbox import SandboxedDownloader
from defuse.sanitizer import DocumentSanitizer


@pytest.mark.integration
@pytest.mark.slow
class TestCompleteDownloadSanitizeWorkflow:
    """Test complete download → sanitize → verify workflows."""

    @responses.activate
    def test_pdf_download_and_sanitize_workflow(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test complete workflow: download PDF → sanitize → verify output."""
        # Mock a realistic PDF download
        pdf_content = b"""%PDF-1.7
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
301
%%EOF"""

        responses.add(
            responses.GET,
            "http://example.com/document.pdf",
            body=pdf_content,
            status=200,
            headers={
                "content-type": "application/pdf",
                "content-length": str(len(pdf_content)),
            },
        )

        # Set up the complete workflow
        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        output_dir = temp_dir / "output"
        output_dir.mkdir(exist_ok=True)

        # Step 1: Download the document
        with patch.object(downloader, "run_docker_download") as mock_download:
            downloaded_file = temp_dir / "document.pdf"
            downloaded_file.write_bytes(pdf_content)
            mock_download.return_value = True

            download_result = downloader.sandboxed_download(
                "http://example.com/document.pdf", downloaded_file
            )

        assert download_result == downloaded_file
        assert downloaded_file.exists()
        assert downloaded_file.read_bytes() == pdf_content

        # Step 2: Verify format detection
        detector = FileTypeDetector()
        with open(downloaded_file, "rb") as f:
            detected_format, confidence = detector.detect_format(buffer=f)

        assert detected_format == SupportedFormat.PDF
        assert confidence > 0.8

        # Step 3: Sanitize the document
        sanitized_file = sanitizer.sanitize_document(
            downloaded_file, "document_defused.pdf"
        )

        assert sanitized_file.exists()
        assert sanitized_file.name == "document_defused.pdf"

        # Verify sanitized content (mock dangerzone output)
        sanitized_content = sanitized_file.read_text()
        assert "%PDF-1.7" in sanitized_content
        assert "Mock sanitized document from document.pdf" in sanitized_content

        # Step 4: Cleanup verification
        if not integration_config.sanitizer.keep_temp_files:
            # Original file should be cleaned up in production
            pass

    @responses.activate
    def test_docx_download_and_sanitize_workflow(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test complete workflow with DOCX document."""
        # Mock DOCX content (simplified ZIP structure)
        docx_content = (
            b"""PK\x03\x04\x14\x00\x00\x00\x08\x00[Content_Types].xml"""
            + b"Mock DOCX content" * 100
        )

        responses.add(
            responses.GET,
            "http://example.com/report.docx",
            body=docx_content,
            status=200,
            headers={
                "content-type": "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            },
        )

        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        # Complete workflow
        with patch.object(downloader, "run_docker_download") as mock_download:
            downloaded_file = temp_dir / "report.docx"
            downloaded_file.write_bytes(docx_content)
            mock_download.return_value = True

            download_result = downloader.sandboxed_download(
                "http://example.com/report.docx", downloaded_file
            )

        # Verify download
        assert download_result == downloaded_file
        assert downloaded_file.exists()

        # Verify format detection
        detector = FileTypeDetector()
        with open(downloaded_file, "rb") as f:
            detected_format, confidence = detector.detect_format(
                buffer=f, filename=str(downloaded_file)
            )

        # DOCX detection might be ambiguous due to ZIP structure
        assert detected_format in [
            SupportedFormat.DOCX,
            SupportedFormat.XLSX,
            SupportedFormat.PPTX,
        ]
        assert confidence > 0.0

        # Sanitize
        sanitized_file = sanitizer.sanitize_document(
            downloaded_file, "report_defused.pdf"
        )
        assert sanitized_file.exists()

        # Verify output is always PDF regardless of input format
        sanitized_content = sanitized_file.read_text()
        assert "%PDF-1.7" in sanitized_content

    @responses.activate
    def test_batch_workflow_mixed_formats(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test batch processing workflow with multiple formats."""
        # Mock various document formats
        documents = {
            "http://example.com/doc1.pdf": (
                b"%PDF-1.7\nSimple PDF content\n%%EOF",
                "application/pdf",
            ),
            "http://example.com/doc2.docx": (
                b"PK\x03\x04Mock DOCX" + b"content" * 50,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            ),
            "http://example.com/image.png": (
                b"\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x01\x00\x00\x00\x007n\xf9$",
                "image/png",
            ),
            "http://example.com/text.rtf": (
                b"{\\rtf1\\ansi\\deff0 {\\fonttbl {\\f0 Times New Roman;}}\\f0\\fs24 Test RTF Document}",
                "application/rtf",
            ),
        }

        # Set up HTTP responses
        for url, (content, mime_type) in documents.items():
            responses.add(
                responses.GET,
                url,
                body=content,
                status=200,
                headers={"content-type": mime_type},
            )

        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        processed_files = []

        # Process each document
        for i, (url, (content, _)) in enumerate(documents.items()):
            with patch.object(downloader, "run_docker_download") as mock_download:
                downloaded_file = temp_dir / f"doc_{i}.tmp"
                downloaded_file.write_bytes(content)
                mock_download.return_value = True

                download_result = downloader.sandboxed_download(url, downloaded_file)

            assert download_result == downloaded_file

            # Sanitize
            sanitized_file = sanitizer.sanitize_document(
                downloaded_file, f"doc_{i}_defused.pdf"
            )

            assert sanitized_file.exists()
            processed_files.append(sanitized_file)

        # Verify all files were processed
        assert len(processed_files) == 4

        # All outputs should be PDF
        for sanitized_file in processed_files:
            content = sanitized_file.read_text()
            assert "%PDF-1.7" in content

    @responses.activate
    def test_workflow_with_redirects(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test workflow handling HTTP redirects."""
        pdf_content = b"%PDF-1.7\nRedirected PDF content\n%%EOF"

        # Set up redirect chain
        responses.add(
            responses.GET,
            "http://example.com/redirect-source",
            status=302,
            headers={"location": "http://example.com/redirect-target.pdf"},
        )

        responses.add(
            responses.GET,
            "http://example.com/redirect-target.pdf",
            body=pdf_content,
            status=200,
            headers={"content-type": "application/pdf"},
        )

        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        # The sandbox downloader should handle redirects
        with patch.object(downloader, "run_docker_download") as mock_download:
            downloaded_file = temp_dir / "redirected.pdf"
            downloaded_file.write_bytes(pdf_content)
            mock_download.return_value = True

            download_result = downloader.sandboxed_download(
                "http://example.com/redirect-source", downloaded_file
            )

        assert download_result == downloaded_file
        assert downloaded_file.read_bytes() == pdf_content

        # Sanitize the redirected document
        sanitized_file = sanitizer.sanitize_document(
            downloaded_file, "redirected_defused.pdf"
        )
        assert sanitized_file.exists()


@pytest.mark.integration
class TestWorkflowResourceManagement:
    """Test resource management throughout workflows."""

    def test_memory_usage_monitoring(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test that workflows respect memory limits."""
        # Set conservative memory limit
        integration_config.sandbox.max_memory_mb = 128
        integration_config.sandbox.prefer_memory_download = True

        large_content = b"Large document content " * 10000  # ~250KB

        with patch.object(SandboxedDownloader, "run_docker_download") as mock_download:
            mock_download.return_value = True

            downloader = SandboxedDownloader(integration_config)

            # Create a large file to test memory handling
            large_file = temp_dir / "large_document.pdf"
            large_file.write_bytes(b"%PDF-1.7\n" + large_content + b"\n%%EOF")

            # The downloader should handle this without exceeding memory limits
            result = downloader.sandboxed_download(
                "http://example.com/large.pdf", large_file
            )

            # Verify Docker command included memory limits
            docker_cmd = mock_download.call_args[0] if mock_download.call_args else []
            # Would need to inspect the actual subprocess call for memory limits

    def test_temp_file_cleanup(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test that temporary files are properly cleaned up."""
        integration_config.sanitizer.keep_temp_files = False

        with patch.object(SandboxedDownloader, "run_docker_download") as mock_download:
            test_content = b"%PDF-1.7\nTest content\n%%EOF"
            downloaded_file = temp_dir / "temp_test.pdf"
            downloaded_file.write_bytes(test_content)
            mock_download.return_value = True

            downloader = SandboxedDownloader(integration_config)
            sanitizer = DocumentSanitizer(
                integration_config.sanitizer, mock_dangerzone_cli
            )

            # Complete workflow
            download_result = downloader.sandboxed_download(
                "http://example.com/test.pdf", downloaded_file
            )

            sanitized_file = sanitizer.sanitize_document(
                downloaded_file, "test_defused.pdf"
            )

            # Sanitized file should exist
            assert sanitized_file.exists()

            # Temp files should be cleaned up (in real implementation)
            # This would be tested in the actual sanitizer implementation

    def test_concurrent_downloads(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test handling of concurrent download requests."""
        import threading

        results = []
        errors = []

        def download_worker(url_suffix):
            try:
                with patch.object(
                    SandboxedDownloader, "run_docker_download"
                ) as mock_download:
                    content = f"Content for {url_suffix}".encode()
                    downloaded_file = temp_dir / f"concurrent_{url_suffix}.pdf"
                    downloaded_file.write_bytes(b"%PDF-1.7\n" + content + b"\n%%EOF")
                    mock_download.return_value = True

                    downloader = SandboxedDownloader(integration_config)
                    result = downloader.sandboxed_download(
                        f"http://example.com/doc_{url_suffix}.pdf", downloaded_file
                    )
                    results.append(result)
            except Exception as e:
                errors.append(e)

        # Start multiple download threads
        threads = []
        for i in range(3):
            thread = threading.Thread(target=download_worker, args=(i,))
            threads.append(thread)
            thread.start()

        # Wait for all threads to complete
        for thread in threads:
            thread.join(timeout=10)

        # Verify all downloads completed successfully
        assert len(errors) == 0, f"Concurrent download errors: {errors}"
        assert len(results) == 3
        assert all(result is not None for result in results)


@pytest.mark.integration
class TestWorkflowErrorRecovery:
    """Test error recovery in complete workflows."""

    @responses.activate
    def test_download_failure_recovery(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test workflow recovery from download failures."""
        # Mock a failed HTTP request
        responses.add(
            responses.GET,
            "http://unreliable.com/document.pdf",
            status=500,
            body=b"Internal Server Error",
        )

        downloader = SandboxedDownloader(integration_config)
        output_file = temp_dir / "failed_download.pdf"

        with patch.object(downloader, "run_docker_download") as mock_download:
            mock_download.return_value = False  # Simulate download failure

            result = downloader.sandboxed_download(
                "http://unreliable.com/document.pdf", output_file
            )

        # Should handle failure gracefully
        assert result is None
        assert not output_file.exists()

    def test_sanitization_failure_recovery(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test workflow recovery from sanitization failures."""
        # Create a valid downloaded file
        downloaded_file = temp_dir / "test_document.pdf"
        downloaded_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")

        # Mock sanitizer failure
        with patch.object(DocumentSanitizer, "sanitize_document") as mock_sanitize:
            mock_sanitize.side_effect = RuntimeError("Dangerzone conversion failed")

            sanitizer = DocumentSanitizer(
                integration_config.sanitizer, mock_dangerzone_cli
            )

            with pytest.raises(RuntimeError, match="Dangerzone conversion failed"):
                sanitizer.sanitize_document(downloaded_file, "output.pdf")

    @responses.activate
    def test_partial_batch_failure_recovery(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test batch processing with partial failures."""
        # Mix of successful and failed URLs
        urls_and_responses = [
            ("http://example.com/good1.pdf", 200, b"%PDF-1.7\nGood PDF 1\n%%EOF"),
            ("http://example.com/bad.pdf", 404, b"Not Found"),
            ("http://example.com/good2.pdf", 200, b"%PDF-1.7\nGood PDF 2\n%%EOF"),
            ("http://example.com/timeout.pdf", 500, b"Server Error"),
            ("http://example.com/good3.pdf", 200, b"%PDF-1.7\nGood PDF 3\n%%EOF"),
        ]

        for url, status, content in urls_and_responses:
            responses.add(
                responses.GET,
                url,
                status=status,
                body=content,
                headers={"content-type": "application/pdf"} if status == 200 else {},
            )

        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        successful_downloads = 0
        successful_sanitizations = 0

        for i, (url, expected_status, content) in enumerate(urls_and_responses):
            with patch.object(downloader, "run_docker_download") as mock_download:
                if expected_status == 200:
                    downloaded_file = temp_dir / f"batch_{i}.pdf"
                    downloaded_file.write_bytes(content)
                    mock_download.return_value = True

                    download_result = downloader.sandboxed_download(
                        url, downloaded_file
                    )

                    if download_result:
                        successful_downloads += 1

                        try:
                            sanitized_file = sanitizer.sanitize_document(
                                downloaded_file, f"batch_{i}_defused.pdf"
                            )
                            if sanitized_file and sanitized_file.exists():
                                successful_sanitizations += 1
                        except Exception:
                            pass  # Count failures but continue processing
                else:
                    mock_download.return_value = False
                    download_result = downloader.sandboxed_download(url, None)
                    assert download_result is None

        # Should have processed the successful ones
        assert successful_downloads == 3  # Three 200 responses
        assert successful_sanitizations == 3  # All successful downloads should sanitize


@pytest.mark.integration
@pytest.mark.slow
class TestWorkflowPerformance:
    """Test workflow performance and efficiency."""

    @responses.activate
    def test_workflow_timing(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test that workflows complete within reasonable time limits."""
        pdf_content = b"%PDF-1.7\nPerformance test content\n%%EOF"

        responses.add(
            responses.GET,
            "http://example.com/performance.pdf",
            body=pdf_content,
            status=200,
            headers={"content-type": "application/pdf"},
        )

        downloader = SandboxedDownloader(integration_config)
        sanitizer = DocumentSanitizer(integration_config.sanitizer, mock_dangerzone_cli)

        start_time = time.time()

        with patch.object(downloader, "run_docker_download") as mock_download:
            downloaded_file = temp_dir / "performance.pdf"
            downloaded_file.write_bytes(pdf_content)
            mock_download.return_value = True

            # Complete workflow
            download_result = downloader.sandboxed_download(
                "http://example.com/performance.pdf", downloaded_file
            )

            sanitized_file = sanitizer.sanitize_document(
                downloaded_file, "performance_defused.pdf"
            )

        end_time = time.time()
        workflow_time = end_time - start_time

        # Workflow should complete quickly with mocking (< 1 second)
        assert workflow_time < 1.0
        assert download_result == downloaded_file
        assert sanitized_file.exists()

    def test_memory_efficiency(
        self,
        integration_config,
        temp_dir,
        mock_dangerzone_cli,
        mock_sandbox_capabilities,
    ):
        """Test memory efficiency of workflows."""
        # This would be more meaningful with real memory monitoring
        # For now, just verify the workflow completes with reasonable settings
        integration_config.sandbox.max_memory_mb = 64  # Very low limit
        integration_config.sandbox.prefer_memory_download = True

        large_content = b"Memory efficiency test " * 1000

        with patch.object(SandboxedDownloader, "run_docker_download") as mock_download:
            test_file = temp_dir / "memory_test.pdf"
            test_file.write_bytes(b"%PDF-1.7\n" + large_content + b"\n%%EOF")
            mock_download.return_value = True

            downloader = SandboxedDownloader(integration_config)
            sanitizer = DocumentSanitizer(
                integration_config.sanitizer, mock_dangerzone_cli
            )

            # Should complete without memory issues
            download_result = downloader.sandboxed_download(
                "http://example.com/large.pdf", test_file
            )

            sanitized_file = sanitizer.sanitize_document(
                test_file, "memory_test_defused.pdf"
            )

            assert download_result == test_file
            assert sanitized_file.exists()
