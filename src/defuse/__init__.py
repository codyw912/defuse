"""
Defuse - Secure document download and sanitization tool using Dangerzone.

This package provides tools for securely downloading documents from the web and
sanitizing them using Dangerzone to remove potential threats. Supports all
file types that Dangerzone handles: PDFs, Office documents, images, and more.
"""

__version__ = "0.1.0"
__author__ = "Defuse Contributors"
__description__ = "Secure document download and sanitization tool using Dangerzone"

from .config import Config, get_default_config
from .downloader import SecureDocumentDownloader, DocumentDownloadError
from .sanitizer import DocumentSanitizer, DocumentSanitizeError
from .sandbox import (
    SandboxedDownloader,
    get_sandbox_capabilities,
    IsolationLevel,
    SandboxBackend,
)
from .formats import FileTypeDetector, SupportedFormat

__all__ = [
    "Config",
    "get_default_config",
    "SecureDocumentDownloader",
    "DocumentDownloadError",
    "DocumentSanitizer",
    "DocumentSanitizeError",
    "SandboxedDownloader",
    "get_sandbox_capabilities",
    "IsolationLevel",
    "SandboxBackend",
    "FileTypeDetector",
    "SupportedFormat",
]
