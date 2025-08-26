"""
File format detection and validation for all Dangerzone-supported types.
"""

import io
from enum import Enum
from pathlib import Path
from typing import Optional, BinaryIO, Tuple, Dict, List, Set
from dataclasses import dataclass


class SupportedFormat(Enum):
    """All file formats supported by Dangerzone"""

    # Documents
    PDF = "pdf"
    DOC = "doc"  # Legacy Word
    DOCX = "docx"  # Modern Word
    XLS = "xls"  # Legacy Excel
    XLSX = "xlsx"  # Modern Excel
    PPT = "ppt"  # Legacy PowerPoint
    PPTX = "pptx"  # Modern PowerPoint
    ODT = "odt"  # OpenDocument Text
    ODS = "ods"  # OpenDocument Spreadsheet
    ODP = "odp"  # OpenDocument Presentation
    ODG = "odg"  # OpenDocument Graphics
    RTF = "rtf"  # Rich Text Format
    EPUB = "epub"  # E-book format
    HWP = "hwp"  # Hancom Office
    HWPX = "hwpx"  # Hancom Office XML

    # Images
    JPEG = "jpeg"
    PNG = "png"
    GIF = "gif"
    TIFF = "tiff"
    BMP = "bmp"
    SVG = "svg"
    WEBP = "webp"


@dataclass
class FormatInfo:
    """Information about a file format"""

    format: SupportedFormat
    mime_types: List[str]
    extensions: List[str]
    magic_bytes: List[bytes]
    description: str


class FileTypeDetector:
    """Detects file types based on magic bytes, MIME types, and extensions"""

    def __init__(self):
        self.format_registry = self._build_format_registry()
        self.magic_to_format = self._build_magic_index()
        self.mime_to_format = self._build_mime_index()
        self.ext_to_format = self._build_extension_index()

    def _build_format_registry(self) -> Dict[SupportedFormat, FormatInfo]:
        """Build complete format registry with detection info"""
        return {
            # Documents
            SupportedFormat.PDF: FormatInfo(
                format=SupportedFormat.PDF,
                mime_types=["application/pdf"],
                extensions=[".pdf"],
                magic_bytes=[b"%PDF"],
                description="Portable Document Format",
            ),
            SupportedFormat.DOCX: FormatInfo(
                format=SupportedFormat.DOCX,
                mime_types=[
                    "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
                ],
                extensions=[".docx"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature (DOCX is ZIP-based)
                description="Microsoft Word Document (Modern)",
            ),
            SupportedFormat.DOC: FormatInfo(
                format=SupportedFormat.DOC,
                mime_types=["application/msword"],
                extensions=[".doc"],
                magic_bytes=[b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE signature
                description="Microsoft Word Document (Legacy)",
            ),
            SupportedFormat.XLSX: FormatInfo(
                format=SupportedFormat.XLSX,
                mime_types=[
                    "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                ],
                extensions=[".xlsx"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="Microsoft Excel Spreadsheet (Modern)",
            ),
            SupportedFormat.XLS: FormatInfo(
                format=SupportedFormat.XLS,
                mime_types=["application/vnd.ms-excel"],
                extensions=[".xls"],
                magic_bytes=[b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE signature
                description="Microsoft Excel Spreadsheet (Legacy)",
            ),
            SupportedFormat.PPTX: FormatInfo(
                format=SupportedFormat.PPTX,
                mime_types=[
                    "application/vnd.openxmlformats-officedocument.presentationml.presentation"
                ],
                extensions=[".pptx"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="Microsoft PowerPoint Presentation (Modern)",
            ),
            SupportedFormat.PPT: FormatInfo(
                format=SupportedFormat.PPT,
                mime_types=["application/vnd.ms-powerpoint"],
                extensions=[".ppt"],
                magic_bytes=[b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1"],  # OLE signature
                description="Microsoft PowerPoint Presentation (Legacy)",
            ),
            SupportedFormat.ODT: FormatInfo(
                format=SupportedFormat.ODT,
                mime_types=["application/vnd.oasis.opendocument.text"],
                extensions=[".odt"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature (ODF is ZIP-based)
                description="OpenDocument Text",
            ),
            SupportedFormat.ODS: FormatInfo(
                format=SupportedFormat.ODS,
                mime_types=["application/vnd.oasis.opendocument.spreadsheet"],
                extensions=[".ods"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="OpenDocument Spreadsheet",
            ),
            SupportedFormat.ODP: FormatInfo(
                format=SupportedFormat.ODP,
                mime_types=["application/vnd.oasis.opendocument.presentation"],
                extensions=[".odp"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="OpenDocument Presentation",
            ),
            SupportedFormat.ODG: FormatInfo(
                format=SupportedFormat.ODG,
                mime_types=["application/vnd.oasis.opendocument.graphics"],
                extensions=[".odg"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="OpenDocument Graphics",
            ),
            SupportedFormat.RTF: FormatInfo(
                format=SupportedFormat.RTF,
                mime_types=["application/rtf", "text/rtf"],
                extensions=[".rtf"],
                magic_bytes=[b"{\\rtf"],
                description="Rich Text Format",
            ),
            SupportedFormat.EPUB: FormatInfo(
                format=SupportedFormat.EPUB,
                mime_types=["application/epub+zip"],
                extensions=[".epub"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="Electronic Publication",
            ),
            SupportedFormat.HWP: FormatInfo(
                format=SupportedFormat.HWP,
                mime_types=["application/x-hwp"],
                extensions=[".hwp"],
                magic_bytes=[b"HWP Document File"],
                description="Hancom Office Document",
            ),
            SupportedFormat.HWPX: FormatInfo(
                format=SupportedFormat.HWPX,
                mime_types=["application/hwp+zip"],
                extensions=[".hwpx"],
                magic_bytes=[b"PK\x03\x04"],  # ZIP signature
                description="Hancom Office Document (XML)",
            ),
            # Images
            SupportedFormat.JPEG: FormatInfo(
                format=SupportedFormat.JPEG,
                mime_types=["image/jpeg", "image/jpg"],
                extensions=[".jpg", ".jpeg"],
                magic_bytes=[b"\xff\xd8\xff"],
                description="JPEG Image",
            ),
            SupportedFormat.PNG: FormatInfo(
                format=SupportedFormat.PNG,
                mime_types=["image/png"],
                extensions=[".png"],
                magic_bytes=[b"\x89PNG\r\n\x1a\n"],
                description="PNG Image",
            ),
            SupportedFormat.GIF: FormatInfo(
                format=SupportedFormat.GIF,
                mime_types=["image/gif"],
                extensions=[".gif"],
                magic_bytes=[b"GIF87a", b"GIF89a"],
                description="GIF Image",
            ),
            SupportedFormat.TIFF: FormatInfo(
                format=SupportedFormat.TIFF,
                mime_types=["image/tiff"],
                extensions=[".tif", ".tiff"],
                magic_bytes=[b"II*\x00", b"MM\x00*"],  # Little-endian and big-endian
                description="TIFF Image",
            ),
            SupportedFormat.BMP: FormatInfo(
                format=SupportedFormat.BMP,
                mime_types=["image/bmp"],
                extensions=[".bmp"],
                magic_bytes=[b"BM"],
                description="Bitmap Image",
            ),
            SupportedFormat.SVG: FormatInfo(
                format=SupportedFormat.SVG,
                mime_types=["image/svg+xml"],
                extensions=[".svg"],
                magic_bytes=[b"<?xml", b"<svg"],
                description="Scalable Vector Graphics",
            ),
            SupportedFormat.WEBP: FormatInfo(
                format=SupportedFormat.WEBP,
                mime_types=["image/webp"],
                extensions=[".webp"],
                magic_bytes=[b"RIFF"],  # Followed by WEBP later in header
                description="WebP Image",
            ),
        }

    def _build_magic_index(self) -> Dict[bytes, List[SupportedFormat]]:
        """Build index of magic bytes to formats"""
        index: Dict[bytes, List[SupportedFormat]] = {}
        for format_info in self.format_registry.values():
            for magic in format_info.magic_bytes:
                if magic not in index:
                    index[magic] = []
                index[magic].append(format_info.format)
        return index

    def _build_mime_index(self) -> Dict[str, List[SupportedFormat]]:
        """Build index of MIME types to formats"""
        index: Dict[str, List[SupportedFormat]] = {}
        for format_info in self.format_registry.values():
            for mime in format_info.mime_types:
                if mime not in index:
                    index[mime] = []
                index[mime].append(format_info.format)
        return index

    def _build_extension_index(self) -> Dict[str, List[SupportedFormat]]:
        """Build index of extensions to formats"""
        index: Dict[str, List[SupportedFormat]] = {}
        for format_info in self.format_registry.values():
            for ext in format_info.extensions:
                ext_lower = ext.lower()
                if ext_lower not in index:
                    index[ext_lower] = []
                index[ext_lower].append(format_info.format)
        return index

    def detect_from_header(
        self, buffer: BinaryIO, max_read: int = 1024
    ) -> Optional[SupportedFormat]:
        """Detect format from file header/magic bytes"""
        current_pos = buffer.tell()
        buffer.seek(0)

        try:
            header = buffer.read(max_read)
            if not header:
                return None

            # Check each magic byte signature
            for magic, formats in self.magic_to_format.items():
                if header.startswith(magic):
                    # For formats that share magic bytes (like ZIP-based formats),
                    # we need additional checks
                    if magic == b"PK\x03\x04":  # ZIP signature
                        return self._detect_zip_based_format(buffer, header)
                    elif magic == b"\xd0\xcf\x11\xe0\xa1\xb1\x1a\xe1":  # OLE signature
                        return self._detect_ole_based_format(buffer, header)
                    else:
                        # Return first matching format for unique magic bytes
                        return formats[0]

            return None

        finally:
            buffer.seek(current_pos)

    def _detect_zip_based_format(
        self, buffer: BinaryIO, header: bytes
    ) -> Optional[SupportedFormat]:
        """Detect specific ZIP-based format (DOCX, XLSX, PPTX, ODT, etc.)"""
        # This is simplified - in practice you'd look for specific files within the ZIP
        # For now, return the most common format (DOCX) or None
        # A full implementation would extract the ZIP and look for identifying files
        return SupportedFormat.DOCX  # Default assumption

    def _detect_ole_based_format(
        self, buffer: BinaryIO, header: bytes
    ) -> Optional[SupportedFormat]:
        """Detect specific OLE-based format (DOC, XLS, PPT)"""
        # This is simplified - in practice you'd examine the OLE structure
        # For now, return the most common format (DOC) or None
        return SupportedFormat.DOC  # Default assumption

    def detect_from_mime_type(self, mime_type: str) -> List[SupportedFormat]:
        """Detect formats from MIME type"""
        return self.mime_to_format.get(mime_type.lower(), [])

    def detect_from_extension(self, filename: str) -> List[SupportedFormat]:
        """Detect formats from file extension"""
        path = Path(filename)
        ext = path.suffix.lower()
        return self.ext_to_format.get(ext, [])

    def detect_format(
        self,
        buffer: Optional[BinaryIO] = None,
        mime_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> Tuple[Optional[SupportedFormat], float]:
        """
        Detect format using all available information

        Returns:
            Tuple of (format, confidence) where confidence is 0.0-1.0
        """
        candidates = {}

        # Magic byte detection (highest confidence)
        if buffer:
            magic_format = self.detect_from_header(buffer)
            if magic_format:
                candidates[magic_format] = 0.9

        # MIME type detection (medium confidence)
        if mime_type:
            mime_formats = self.detect_from_mime_type(mime_type)
            for fmt in mime_formats:
                candidates[fmt] = max(candidates.get(fmt, 0), 0.7)

        # Extension detection (lowest confidence)
        if filename:
            ext_formats = self.detect_from_extension(filename)
            for fmt in ext_formats:
                candidates[fmt] = max(candidates.get(fmt, 0), 0.3)

        if not candidates:
            return None, 0.0

        # Return format with highest confidence
        best_format = max(candidates.items(), key=lambda x: x[1])
        return best_format[0], best_format[1]

    def is_supported(
        self,
        buffer: Optional[BinaryIO] = None,
        mime_type: Optional[str] = None,
        filename: Optional[str] = None,
    ) -> bool:
        """Check if file format is supported by Dangerzone"""
        format, confidence = self.detect_format(buffer, mime_type, filename)
        return format is not None and confidence > 0.0

    def get_format_info(self, format: SupportedFormat) -> FormatInfo:
        """Get information about a specific format"""
        return self.format_registry[format]

    def get_supported_extensions(self) -> Set[str]:
        """Get all supported file extensions"""
        extensions = set()
        for format_info in self.format_registry.values():
            extensions.update(format_info.extensions)
        return extensions

    def get_supported_mime_types(self) -> Set[str]:
        """Get all supported MIME types"""
        mime_types = set()
        for format_info in self.format_registry.values():
            mime_types.update(format_info.mime_types)
        return mime_types


def create_file_detector() -> FileTypeDetector:
    """Create a configured file type detector"""
    return FileTypeDetector()


def is_supported_format(
    buffer: Optional[BinaryIO] = None,
    mime_type: Optional[str] = None,
    filename: Optional[str] = None,
) -> bool:
    """Quick check if a file format is supported"""
    detector = create_file_detector()
    return detector.is_supported(buffer, mime_type, filename)
