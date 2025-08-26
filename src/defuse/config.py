import os
from pathlib import Path
from typing import List, Optional
from dataclasses import dataclass


@dataclass
class SandboxConfig:
    """Configuration for sandbox environment"""

    temp_dir: Path = Path("/tmp/pdf-sandbox")
    max_file_size: int = 100 * 1024 * 1024  # 100MB
    download_timeout: int = 30
    allowed_domains: Optional[List[str]] = None
    user_agent: str = "Mozilla/5.0 (compatible; PDF-Sanitizer/1.0)"

    # Memory and resource limits
    max_memory_mb: int = 512  # Maximum memory for download process
    max_memory_buffer_mb: int = 10  # Size before spilling to disk
    max_cpu_seconds: int = 60  # CPU time limit

    # Security options
    prefer_memory_download: bool = True  # Use memory-first downloads
    enable_certificate_pinning: bool = False  # Pin certificates for known domains
    isolation_level: str = "strict"  # none, basic, strict, paranoid
    sandbox_backend: str = "auto"  # auto, subprocess, firejail, bubblewrap, docker


@dataclass
class SanitizerConfig:
    """Configuration for document sanitization"""

    output_dir: Path = Path.home() / "Downloads"
    keep_temp_files: bool = False
    ocr_lang: Optional[str] = None  # Language for OCR (e.g., 'eng', 'fra')
    archive_original: bool = False  # Archive unsafe originals
    keep_unsafe_files: bool = False  # Keep archived unsafe files


@dataclass
class Config:
    """Main application configuration"""

    sandbox: SandboxConfig
    sanitizer: SanitizerConfig
    verbose: bool = False
    dangerzone_path: Optional[Path] = None

    def __init__(self):
        self.sandbox = SandboxConfig()
        self.sanitizer = SanitizerConfig()

        # Create necessary directories
        self.sandbox.temp_dir.mkdir(parents=True, exist_ok=True)
        self.sanitizer.output_dir.mkdir(parents=True, exist_ok=True)


def get_default_config() -> Config:
    """Get default configuration instance"""
    return Config()


def validate_config(config: Config) -> List[str]:
    """Validate configuration and return list of errors"""
    errors = []

    if config.sandbox.max_file_size <= 0:
        errors.append("Max file size must be positive")

    if config.sandbox.download_timeout <= 0:
        errors.append("Download timeout must be positive")

    return errors
