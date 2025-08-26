"""
Unit tests for file format detection functionality.
"""

import io
from typing import Dict

import pytest

from defuse.formats import (
    FileTypeDetector,
    SupportedFormat,
    FormatInfo,
    create_file_detector,
    is_supported_format,
)


@pytest.mark.unit
class TestSupportedFormat:
    """Test the SupportedFormat enum."""

    def test_all_formats_defined(self):
        """Test that all expected formats are defined."""
        expected_formats = {
            "pdf",
            "doc",
            "docx",
            "xls",
            "xlsx",
            "ppt",
            "pptx",
            "odt",
            "ods",
            "odp",
            "odg",
            "rtf",
            "epub",
            "hwp",
            "hwpx",
            "jpeg",
            "png",
            "gif",
            "tiff",
            "bmp",
            "svg",
            "webp",
        }

        actual_formats = {fmt.value for fmt in SupportedFormat}
        assert actual_formats == expected_formats

    def test_format_values_are_strings(self):
        """Test that all format values are strings."""
        for fmt in SupportedFormat:
            assert isinstance(fmt.value, str)
            assert len(fmt.value) > 0


@pytest.mark.unit
class TestFormatInfo:
    """Test the FormatInfo dataclass."""

    def test_format_info_creation(self):
        """Test creating FormatInfo objects."""
        info = FormatInfo(
            format=SupportedFormat.PDF,
            mime_types=["application/pdf"],
            extensions=[".pdf"],
            magic_bytes=[b"%PDF"],
            description="Portable Document Format",
        )

        assert info.format == SupportedFormat.PDF
        assert info.mime_types == ["application/pdf"]
        assert info.extensions == [".pdf"]
        assert info.magic_bytes == [b"%PDF"]
        assert info.description == "Portable Document Format"


@pytest.mark.unit
class TestFileTypeDetector:
    """Test the FileTypeDetector class."""

    def test_detector_initialization(self):
        """Test detector initializes properly."""
        detector = FileTypeDetector()

        assert isinstance(detector.format_registry, dict)
        assert isinstance(detector.magic_to_format, dict)
        assert isinstance(detector.mime_to_format, dict)
        assert isinstance(detector.ext_to_format, dict)

        # Should have entries for all supported formats
        assert len(detector.format_registry) == len(SupportedFormat)

    def test_magic_byte_detection_pdf(self, sample_pdf_data: bytes):
        """Test magic byte detection for PDF."""
        detector = FileTypeDetector()
        buffer = io.BytesIO(sample_pdf_data)

        detected = detector.detect_from_header(buffer)
        assert detected == SupportedFormat.PDF

    def test_magic_byte_detection_png(self, sample_png_data: bytes):
        """Test magic byte detection for PNG."""
        detector = FileTypeDetector()
        buffer = io.BytesIO(sample_png_data)

        detected = detector.detect_from_header(buffer)
        assert detected == SupportedFormat.PNG

    def test_magic_byte_detection_docx(self, sample_docx_data: bytes):
        """Test magic byte detection for DOCX (ZIP-based)."""
        detector = FileTypeDetector()
        buffer = io.BytesIO(sample_docx_data)

        detected = detector.detect_from_header(buffer)
        # Should detect as DOCX (or at least a ZIP-based format)
        assert detected in [
            SupportedFormat.DOCX,
            SupportedFormat.XLSX,
            SupportedFormat.PPTX,
        ]

    def test_magic_byte_detection_unknown_format(self):
        """Test magic byte detection with unknown format."""
        detector = FileTypeDetector()
        unknown_data = b"UNKNOWN_FORMAT_SIGNATURE"
        buffer = io.BytesIO(unknown_data)

        detected = detector.detect_from_header(buffer)
        assert detected is None

    def test_magic_byte_detection_empty_buffer(self):
        """Test magic byte detection with empty buffer."""
        detector = FileTypeDetector()
        buffer = io.BytesIO(b"")

        detected = detector.detect_from_header(buffer)
        assert detected is None

    def test_mime_type_detection(self):
        """Test MIME type detection."""
        detector = FileTypeDetector()

        # Test known MIME types
        pdf_formats = detector.detect_from_mime_type("application/pdf")
        assert SupportedFormat.PDF in pdf_formats

        png_formats = detector.detect_from_mime_type("image/png")
        assert SupportedFormat.PNG in png_formats

        # Test unknown MIME type
        unknown_formats = detector.detect_from_mime_type("application/unknown")
        assert len(unknown_formats) == 0

    def test_extension_detection(self):
        """Test file extension detection."""
        detector = FileTypeDetector()

        # Test various extensions
        pdf_formats = detector.detect_from_extension("document.pdf")
        assert SupportedFormat.PDF in pdf_formats

        docx_formats = detector.detect_from_extension("report.docx")
        assert SupportedFormat.DOCX in docx_formats

        png_formats = detector.detect_from_extension("image.png")
        assert SupportedFormat.PNG in png_formats

        # Test case insensitive
        pdf_formats_upper = detector.detect_from_extension("DOCUMENT.PDF")
        assert SupportedFormat.PDF in pdf_formats_upper

        # Test unknown extension
        unknown_formats = detector.detect_from_extension("file.unknown")
        assert len(unknown_formats) == 0

    def test_combined_format_detection(self, sample_formats_data: Dict[str, bytes]):
        """Test combined format detection with all methods."""
        detector = FileTypeDetector()

        for format_name, data in sample_formats_data.items():
            buffer = io.BytesIO(data)

            # Test with just buffer
            detected_format, confidence = detector.detect_format(buffer=buffer)
            if format_name in ["pdf", "png", "jpeg", "gif", "rtf"]:
                # These have unique magic bytes, should be detected with high confidence
                assert detected_format is not None
                assert confidence >= 0.9

            # Test with buffer and filename
            filename = f"test.{format_name}"
            detected_format, confidence = detector.detect_format(
                buffer=buffer, filename=filename
            )
            assert detected_format is not None
            assert confidence > 0.0

    def test_format_detection_confidence_levels(self, sample_pdf_data: bytes):
        """Test confidence levels for format detection."""
        detector = FileTypeDetector()
        buffer = io.BytesIO(sample_pdf_data)

        # Magic bytes should give highest confidence
        detected, confidence = detector.detect_format(buffer=buffer)
        assert detected == SupportedFormat.PDF
        assert confidence == 0.9  # Magic byte confidence

        # MIME type should give medium confidence
        detected, confidence = detector.detect_format(mime_type="application/pdf")
        assert detected == SupportedFormat.PDF
        assert confidence == 0.7  # MIME type confidence

        # Extension should give lowest confidence
        detected, confidence = detector.detect_format(filename="test.pdf")
        assert detected == SupportedFormat.PDF
        assert confidence == 0.3  # Extension confidence

        # Combined should use highest confidence
        detected, confidence = detector.detect_format(
            buffer=buffer, mime_type="application/pdf", filename="test.pdf"
        )
        assert detected == SupportedFormat.PDF
        assert confidence == 0.9  # Should use magic byte confidence

    def test_is_supported_method(self, sample_formats_data: Dict[str, bytes]):
        """Test the is_supported convenience method."""
        detector = FileTypeDetector()

        for format_name, data in sample_formats_data.items():
            buffer = io.BytesIO(data)
            filename = f"test.{format_name}"

            # Should be supported with buffer
            assert detector.is_supported(buffer=buffer)

            # Should be supported with filename
            assert detector.is_supported(filename=filename)

        # Should not be supported for unknown format
        unknown_buffer = io.BytesIO(b"UNKNOWN_FORMAT")
        assert not detector.is_supported(buffer=unknown_buffer)

        assert not detector.is_supported(filename="test.unknown")

    def test_get_format_info(self):
        """Test getting format information."""
        detector = FileTypeDetector()

        pdf_info = detector.get_format_info(SupportedFormat.PDF)
        assert isinstance(pdf_info, FormatInfo)
        assert pdf_info.format == SupportedFormat.PDF
        assert "application/pdf" in pdf_info.mime_types
        assert ".pdf" in pdf_info.extensions
        assert any(magic.startswith(b"%PDF") for magic in pdf_info.magic_bytes)

    def test_get_supported_extensions(self):
        """Test getting all supported extensions."""
        detector = FileTypeDetector()
        extensions = detector.get_supported_extensions()

        assert isinstance(extensions, set)
        assert ".pdf" in extensions
        assert ".docx" in extensions
        assert ".png" in extensions
        assert ".jpg" in extensions or ".jpeg" in extensions

        # Should have at least as many extensions as formats
        assert len(extensions) >= len(SupportedFormat)

    def test_get_supported_mime_types(self):
        """Test getting all supported MIME types."""
        detector = FileTypeDetector()
        mime_types = detector.get_supported_mime_types()

        assert isinstance(mime_types, set)
        assert "application/pdf" in mime_types
        assert "image/png" in mime_types
        assert (
            "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            in mime_types
        )

    def test_buffer_position_preserved(self, sample_pdf_data: bytes):
        """Test that buffer position is preserved during detection."""
        detector = FileTypeDetector()
        buffer = io.BytesIO(sample_pdf_data)

        # Move to middle of buffer
        original_position = len(sample_pdf_data) // 2
        buffer.seek(original_position)

        # Detect format
        detector.detect_from_header(buffer)

        # Position should be restored
        assert buffer.tell() == original_position

    def test_zip_based_format_detection(self):
        """Test detection of ZIP-based formats with more specific logic."""
        detector = FileTypeDetector()

        # Test basic ZIP signature detection
        zip_data = b"PK\x03\x04" + b"\x00" * 100  # Basic ZIP structure
        buffer = io.BytesIO(zip_data)

        detected = detector.detect_from_header(buffer)
        # Should detect as some ZIP-based format (implementation returns DOCX as default)
        assert detected in [
            SupportedFormat.DOCX,
            SupportedFormat.XLSX,
            SupportedFormat.PPTX,
            SupportedFormat.ODT,
            SupportedFormat.ODS,
            SupportedFormat.ODP,
            SupportedFormat.EPUB,
            SupportedFormat.HWPX,
        ]

    def test_ole_based_format_detection(self):
        """Test detection of OLE-based formats."""
        detector = FileTypeDetector()

        # OLE signature
        ole_data = b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1" + b"\x00" * 100
        buffer = io.BytesIO(ole_data)

        detected = detector.detect_from_header(buffer)
        # Should detect as some OLE-based format (implementation returns DOC as default)
        assert detected in [
            SupportedFormat.DOC,
            SupportedFormat.XLS,
            SupportedFormat.PPT,
        ]


@pytest.mark.unit
class TestModuleFunctions:
    """Test module-level convenience functions."""

    def test_create_file_detector(self):
        """Test the create_file_detector function."""
        detector = create_file_detector()
        assert isinstance(detector, FileTypeDetector)

    def test_is_supported_format_function(self, sample_pdf_data: bytes):
        """Test the is_supported_format convenience function."""
        buffer = io.BytesIO(sample_pdf_data)

        # Should be supported
        assert is_supported_format(buffer=buffer)
        assert is_supported_format(filename="test.pdf")
        assert is_supported_format(mime_type="application/pdf")

        # Should not be supported
        unknown_buffer = io.BytesIO(b"UNKNOWN")
        assert not is_supported_format(buffer=unknown_buffer)
        assert not is_supported_format(filename="test.unknown")
        assert not is_supported_format(mime_type="application/unknown")


@pytest.mark.unit
class TestFormatSpecificDetection:
    """Test detection for specific file formats."""

    def test_image_formats(self, sample_formats_data: Dict[str, bytes]):
        """Test detection of various image formats."""
        detector = FileTypeDetector()

        image_formats = ["png", "jpeg", "gif"]
        for fmt in image_formats:
            if fmt in sample_formats_data:
                buffer = io.BytesIO(sample_formats_data[fmt])
                detected = detector.detect_from_header(buffer)
                expected = SupportedFormat(fmt)
                assert detected == expected

    def test_document_formats(self, sample_formats_data: Dict[str, bytes]):
        """Test detection of document formats."""
        detector = FileTypeDetector()

        # Test formats with unique signatures
        unique_formats = ["pdf", "rtf"]
        for fmt in unique_formats:
            if fmt in sample_formats_data:
                buffer = io.BytesIO(sample_formats_data[fmt])
                detected = detector.detect_from_header(buffer)
                expected = SupportedFormat(fmt)
                assert detected == expected

    def test_archive_based_formats(self, sample_formats_data: Dict[str, bytes]):
        """Test detection of archive-based formats (ZIP, etc.)."""
        detector = FileTypeDetector()

        # These formats use ZIP structure, so detection may be ambiguous
        zip_based_formats = ["docx", "epub"]
        for fmt in zip_based_formats:
            if fmt in sample_formats_data:
                buffer = io.BytesIO(sample_formats_data[fmt])
                detected = detector.detect_from_header(buffer)
                # Should detect as some ZIP-based format
                assert detected is not None
                assert detected in [
                    SupportedFormat.DOCX,
                    SupportedFormat.XLSX,
                    SupportedFormat.PPTX,
                    SupportedFormat.ODT,
                    SupportedFormat.ODS,
                    SupportedFormat.ODP,
                    SupportedFormat.EPUB,
                    SupportedFormat.HWPX,
                ]


@pytest.mark.unit
class TestErrorConditions:
    """Test error conditions and edge cases."""

    def test_corrupted_data_handling(self):
        """Test handling of corrupted or partial data."""
        detector = FileTypeDetector()

        # Very short data that might match partial signatures
        short_data = b"%P"  # Partial PDF signature
        buffer = io.BytesIO(short_data)

        detected = detector.detect_from_header(buffer)
        # Should not detect with incomplete signature
        assert detected is None

    def test_large_buffer_handling(self):
        """Test handling of large buffers."""
        detector = FileTypeDetector()

        # Create large buffer with PDF signature
        large_data = b"%PDF-1.7\n" + b"x" * 10000
        buffer = io.BytesIO(large_data)

        detected = detector.detect_from_header(buffer)
        assert detected == SupportedFormat.PDF

    def test_invalid_inputs(self):
        """Test handling of invalid inputs."""
        detector = FileTypeDetector()

        # Test with None inputs
        detected, confidence = detector.detect_format()
        assert detected is None
        assert confidence == 0.0

        # Test with empty strings
        formats = detector.detect_from_mime_type("")
        assert len(formats) == 0

        formats = detector.detect_from_extension("")
        assert len(formats) == 0
