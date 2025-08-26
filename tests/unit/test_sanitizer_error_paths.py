"""
Unit tests for sanitizer error paths and exception handling.

These tests focus on error conditions, validation failures, and edge cases
in document sanitization without requiring actual Dangerzone CLI.
"""

import pytest
from unittest.mock import patch, MagicMock
import subprocess
from pathlib import Path
import tempfile
import shutil

from defuse.sanitizer import DocumentSanitizer, DocumentSanitizeError
from defuse.config import SanitizerConfig


class TestDocumentSanitizerInitialization:
    """Test DocumentSanitizer initialization and validation."""
    
    def test_init_with_none_path(self):
        """Test initialization with None dangerzone path."""
        config = SanitizerConfig()
        
        with pytest.raises(DocumentSanitizeError, match="Dangerzone CLI path not provided"):
            DocumentSanitizer(config, None)
    
    def test_init_with_nonexistent_path(self):
        """Test initialization with nonexistent dangerzone path."""
        config = SanitizerConfig()
        nonexistent_path = Path("/nonexistent/dangerzone-cli")
        
        with pytest.raises(DocumentSanitizeError, match="Dangerzone CLI not found"):
            DocumentSanitizer(config, nonexistent_path)
    
    def test_is_available_with_none_path(self):
        """Test is_available method with None path."""
        config = SanitizerConfig()
        
        # Create sanitizer with valid path first
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            valid_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, valid_path)
            
            # Manually set to None to test the method
            sanitizer.dangerzone_cli = None
            
            assert sanitizer.is_available() is False
        finally:
            valid_path.unlink(missing_ok=True)
    
    def test_is_available_with_missing_file(self):
        """Test is_available method when CLI file goes missing."""
        config = SanitizerConfig()
        
        # Create temporary file then delete it
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            temp_path = Path(tmp.name)
        
        sanitizer = DocumentSanitizer(config, temp_path)
        
        # Delete the file after initialization
        temp_path.unlink()
        
        assert sanitizer.is_available() is False


class TestSanitizeMethodErrorPaths:
    """Test sanitize method error handling."""
    
    def test_sanitize_nonexistent_input_file(self):
        """Test sanitizing nonexistent input file."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            nonexistent_input = Path("/nonexistent/input.pdf")
            
            with pytest.raises(DocumentSanitizeError, match="Input file does not exist"):
                sanitizer.sanitize(nonexistent_input)
        finally:
            dangerzone_path.unlink(missing_ok=True)
    
    def test_sanitize_dangerzone_command_failure(self):
        """Test handling of Dangerzone command failure."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            input_file = Path(tmp.name + ".input.pdf")
            input_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                # Mock failed Dangerzone process
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_result.stderr = "Dangerzone processing failed"
                mock_result.stdout = ""
                mock_run.return_value = mock_result
                
                with pytest.raises(DocumentSanitizeError, match="Dangerzone failed"):
                    sanitizer.sanitize(input_file)
        finally:
            dangerzone_path.unlink(missing_ok=True)
            input_file.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)
    
    def test_sanitize_dangerzone_timeout(self):
        """Test handling of Dangerzone timeout."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            input_file = Path(tmp.name + ".input.pdf")
            input_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("dangerzone-cli", 600)
                
                with pytest.raises(DocumentSanitizeError, match="Dangerzone timed out"):
                    sanitizer.sanitize(input_file)
        finally:
            dangerzone_path.unlink(missing_ok=True)
            input_file.unlink(missing_ok=True) 
            shutil.rmtree(config.output_dir, ignore_errors=True)
    
    def test_sanitize_dangerzone_not_found(self):
        """Test handling when Dangerzone CLI is not found during execution."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            input_file = Path(tmp.name + ".input.pdf")
            input_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("dangerzone-cli: command not found")
                
                with pytest.raises(DocumentSanitizeError, match="Dangerzone CLI not found"):
                    sanitizer.sanitize(input_file)
        finally:
            dangerzone_path.unlink(missing_ok=True)
            input_file.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)
    
    def test_sanitize_output_validation_failure(self):
        """Test handling when output file fails validation."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            input_file = Path(tmp.name + ".input.pdf")
            input_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                # Mock successful Dangerzone process
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stderr = ""
                mock_result.stdout = "Success"
                mock_run.return_value = mock_result
                
                with patch.object(sanitizer, "validate_output", return_value=False):
                    # Create invalid output file (will fail validation)
                    output_path = config.output_dir / "test_defused.pdf"
                    output_path.write_text("Invalid PDF content")
                    
                    with pytest.raises(DocumentSanitizeError, match="Output file failed validation"):
                        sanitizer.sanitize(input_file)
        finally:
            dangerzone_path.unlink(missing_ok=True)
            input_file.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)
    
    def test_sanitize_no_output_file_created(self):
        """Test handling when Dangerzone doesn't create expected output."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            input_file = Path(tmp.name + ".input.pdf")
            input_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                # Mock successful process but no output file created
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stderr = ""
                mock_result.stdout = "Success"
                mock_run.return_value = mock_result
                
                with pytest.raises(DocumentSanitizeError, match="Dangerzone did not create expected output"):
                    sanitizer.sanitize(input_file)
        finally:
            dangerzone_path.unlink(missing_ok=True)
            input_file.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)
    
    def test_sanitize_cleanup_on_error(self):
        """Test that output files are cleaned up when errors occur."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            input_file = Path(tmp.name + ".input.pdf")
            input_file.write_bytes(b"%PDF-1.7\nTest content\n%%EOF")
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                # Mock successful process
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stderr = ""
                mock_result.stdout = "Success"
                mock_run.return_value = mock_result
                
                # Create output file but make validation raise an exception
                output_path = config.output_dir / "test_defused.pdf"
                output_path.write_bytes(b"%PDF-1.7\nValid content\n%%EOF")
                
                with patch.object(sanitizer, "validate_output") as mock_validate:
                    mock_validate.side_effect = Exception("Validation error")
                    
                    with patch("pathlib.Path.unlink") as mock_unlink:
                        with pytest.raises(DocumentSanitizeError, match="Sanitization error"):
                            sanitizer.sanitize(input_file)
                        
                        # Should attempt to clean up output file
                        mock_unlink.assert_called()
        finally:
            dangerzone_path.unlink(missing_ok=True)
            input_file.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)


class TestValidateOutputMethod:
    """Test output validation method edge cases."""
    
    def test_validate_output_nonexistent_file(self):
        """Test validation of nonexistent output file."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            nonexistent_file = Path("/nonexistent/output.pdf")
            
            result = sanitizer.validate_output(nonexistent_file)
            assert result is False
        finally:
            dangerzone_path.unlink(missing_ok=True)
    
    def test_validate_output_empty_file(self):
        """Test validation of empty output file."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            empty_file = Path(tmp.name + ".empty.pdf")
            empty_file.write_bytes(b"")  # Empty file
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            result = sanitizer.validate_output(empty_file)
            assert result is False
        finally:
            dangerzone_path.unlink(missing_ok=True)
            empty_file.unlink(missing_ok=True)
    
    def test_validate_output_small_file(self):
        """Test validation of very small file (below threshold)."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            small_file = Path(tmp.name + ".small.pdf")
            small_file.write_bytes(b"tiny")  # Less than 100 bytes
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            result = sanitizer.validate_output(small_file)
            assert result is False
        finally:
            dangerzone_path.unlink(missing_ok=True)
            small_file.unlink(missing_ok=True)
    
    def test_validate_output_invalid_pdf_header(self):
        """Test validation of file with invalid PDF header."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
            invalid_pdf = Path(tmp.name + ".invalid.pdf")
            # File big enough but wrong header
            invalid_pdf.write_bytes(b"NOT A PDF HEADER" + b"x" * 100)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            result = sanitizer.validate_output(invalid_pdf)
            assert result is False
        finally:
            dangerzone_path.unlink(missing_ok=True)
            invalid_pdf.unlink(missing_ok=True)
    
    def test_validate_output_file_read_error(self):
        """Test validation when file cannot be read."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            # Mock file that exists but raises exception when read
            test_file = Path("/tmp/unreadable.pdf")
            with patch("pathlib.Path.exists", return_value=True):
                with patch("pathlib.Path.stat") as mock_stat:
                    mock_stat.return_value.st_size = 1000  # Big enough
                    
                    with patch("builtins.open") as mock_open:
                        mock_open.side_effect = PermissionError("Permission denied")
                        
                        result = sanitizer.validate_output(test_file)
                        assert result is False
        finally:
            dangerzone_path.unlink(missing_ok=True)


class TestUtilityMethods:
    """Test utility methods and edge cases."""
    
    def test_get_version_command_not_found(self):
        """Test get_version when Dangerzone command is not found."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = FileNotFoundError("Command not found")
                
                version = sanitizer.get_version()
                assert version is None
        finally:
            dangerzone_path.unlink(missing_ok=True)
    
    def test_get_version_command_timeout(self):
        """Test get_version when command times out."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                mock_run.side_effect = subprocess.TimeoutExpired("dangerzone-cli", 10)
                
                version = sanitizer.get_version()
                assert version is None
        finally:
            dangerzone_path.unlink(missing_ok=True)
    
    def test_get_version_command_failure(self):
        """Test get_version when command returns non-zero exit code."""
        config = SanitizerConfig()
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 1
                mock_run.return_value = mock_result
                
                version = sanitizer.get_version()
                assert version is None
        finally:
            dangerzone_path.unlink(missing_ok=True)
    
    def test_cleanup_temp_files_permission_error(self):
        """Test cleanup when permission errors occur."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        config.keep_temp_files = False
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("pathlib.Path.glob") as mock_glob:
                mock_temp_file = MagicMock()
                mock_temp_file.unlink.side_effect = PermissionError("Permission denied")
                mock_glob.return_value = [mock_temp_file]
                
                # Should not raise exception, should handle gracefully
                sanitizer.cleanup_temp_files()
        finally:
            dangerzone_path.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)
    
    def test_cleanup_temp_files_with_keep_temp_files_enabled(self):
        """Test cleanup when keep_temp_files is enabled."""
        config = SanitizerConfig()
        config.output_dir = Path(tempfile.mkdtemp())
        config.keep_temp_files = True  # Don't clean up
        
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            dangerzone_path = Path(tmp.name)
        
        try:
            sanitizer = DocumentSanitizer(config, dangerzone_path)
            
            with patch("pathlib.Path.glob") as mock_glob:
                # Should not be called when keep_temp_files is True
                sanitizer.cleanup_temp_files()
                mock_glob.assert_not_called()
        finally:
            dangerzone_path.unlink(missing_ok=True)
            shutil.rmtree(config.output_dir, ignore_errors=True)