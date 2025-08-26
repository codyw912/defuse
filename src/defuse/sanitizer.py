import subprocess
import shutil
from pathlib import Path
from typing import Optional

from .config import SanitizerConfig


class DocumentSanitizeError(Exception):
    """Custom exception for document sanitization errors"""

    pass


class DocumentSanitizer:
    """Document sanitization using Dangerzone CLI"""

    def __init__(self, config: SanitizerConfig, dangerzone_cli_path: Path):
        self.config = config
        self.dangerzone_cli = dangerzone_cli_path

        if self.dangerzone_cli is None:
            raise DocumentSanitizeError("Dangerzone CLI path not provided")

        if not self.dangerzone_cli.exists():
            raise DocumentSanitizeError(
                f"Dangerzone CLI not found at: {dangerzone_cli_path}"
            )

    def is_available(self) -> bool:
        """Check if Dangerzone CLI is available"""
        return self.dangerzone_cli is not None and self.dangerzone_cli.exists()

    def sanitize(self, input_path: Path, output_filename: Optional[str] = None) -> Path:
        """
        Sanitize document using Dangerzone CLI

        Args:
            input_path: Path to input document
            output_filename: Optional output filename

        Returns:
            Path to sanitized document

        Raises:
            DocumentSanitizeError: If sanitization fails
        """
        if not input_path.exists():
            raise DocumentSanitizeError(f"Input file does not exist: {input_path}")

        # Prepare output path
        if output_filename is None:
            base_name = input_path.stem
            output_filename = f"{base_name}_defused.pdf"

        # Ensure output filename ends with .pdf (Dangerzone always outputs PDF)
        if not output_filename.endswith(".pdf"):
            output_filename = f"{output_filename}.pdf"

        output_path = self.config.output_dir / output_filename

        # Ensure output directory exists
        self.config.output_dir.mkdir(parents=True, exist_ok=True)

        try:
            # Build Dangerzone command
            cmd = [
                str(self.dangerzone_cli),
                str(input_path),
                "--output-filename",
                output_filename,  # Just the filename, not full path
            ]

            # Add OCR if specified
            if hasattr(self.config, "ocr_lang") and self.config.ocr_lang:
                cmd.extend(["--ocr-lang", self.config.ocr_lang])

            # Add archive flag if specified
            if getattr(self.config, "archive_original", False):
                cmd.append("--archive")

            # Run Dangerzone
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=600,  # 10 minute timeout
                cwd=self.config.output_dir,
            )

            if result.returncode != 0:
                error_msg = (
                    result.stderr.strip() if result.stderr else result.stdout.strip()
                )
                raise DocumentSanitizeError(f"Dangerzone failed: {error_msg}")

            # Dangerzone creates files with -safe suffix by default
            # Check if our expected output exists, or find the actual output
            if not output_path.exists():
                # Look for files with -safe suffix
                stem = output_path.stem
                safe_file = output_path.parent / f"{stem}-safe.pdf"
                if safe_file.exists():
                    # Rename to requested filename
                    safe_file.rename(output_path)
                else:
                    # Look for any new files in output directory
                    # (Dangerzone outputs PDF)
                    output_files = list(self.config.output_dir.glob("*"))
                    if output_files:
                        # Use the most recently created one
                        newest_file = max(output_files, key=lambda p: p.stat().st_ctime)
                        if newest_file != output_path and newest_file.is_file():
                            newest_file.rename(output_path)
                    else:
                        raise DocumentSanitizeError(
                            "Dangerzone did not create expected output file"
                        )

            if not self.validate_output(output_path):
                raise DocumentSanitizeError("Output file failed validation")

            return output_path

        except subprocess.TimeoutExpired:
            raise DocumentSanitizeError(
                "Dangerzone timed out (file may be too large or complex)"
            )
        except FileNotFoundError:
            raise DocumentSanitizeError(
                f"Dangerzone CLI not found: {self.dangerzone_cli}"
            )
        except Exception as e:
            if output_path.exists():
                output_path.unlink(missing_ok=True)
            raise DocumentSanitizeError(f"Sanitization error: {str(e)}")

    def validate_output(self, output_path: Path) -> bool:
        """Validate that output file exists and has reasonable size"""
        try:
            if not output_path.exists():
                return False

            # Check file size (Dangerzone always outputs PDF regardless of input)
            if output_path.stat().st_size < 100:
                return False

            # Check PDF magic bytes (Dangerzone always converts to PDF)
            with open(output_path, "rb") as f:
                header = f.read(4)
                if header != b"%PDF":
                    return False

            return True

        except Exception:
            return False

    def get_version(self) -> Optional[str]:
        """Get Dangerzone version"""
        try:
            result = subprocess.run(
                [str(self.dangerzone_cli), "--version"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return result.stdout.strip()
        except Exception:
            pass
        return None

    def cleanup_temp_files(self):
        """Clean up temporary files"""
        if not self.config.keep_temp_files:
            try:
                for temp_file in self.config.output_dir.glob("temp_*"):
                    temp_file.unlink(missing_ok=True)

                # Clean up unsafe archived files if not keeping them
                unsafe_dir = self.config.output_dir / "unsafe"
                if unsafe_dir.exists() and not getattr(
                    self.config, "keep_unsafe_files", False
                ):
                    shutil.rmtree(unsafe_dir, ignore_errors=True)

            except Exception:
                pass
