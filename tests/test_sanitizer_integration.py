"""
Cross-platform sanitizer integration tests.

Tests for Dangerzone CLI detection and sanitization across Linux, Windows, and macOS.
These tests verify that the sanitization process works correctly on each platform
with platform-specific paths and behaviors.
"""

import platform
import tempfile
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from defuse.config import SanitizerConfig
from defuse.sanitizer import DocumentSanitizer
from defuse.cli import find_dangerzone_cli


class TestCrossPlatformSanitizerDetection:
    """Test Dangerzone CLI detection across all platforms."""

    def test_dangerzone_path_detection_logic(self):
        """Test that Dangerzone detection checks appropriate paths for each platform."""
        with patch("defuse.cli.shutil.which", return_value=None):  # Not in PATH
            with patch("defuse.cli.Path.exists") as mock_exists:
                mock_exists.return_value = False  # No paths exist

                _ = find_dangerzone_cli()  # Just testing that it doesn't crash

                # Should have checked platform-appropriate paths
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]

                system = platform.system()
                if system == "Linux":
                    # Should check Linux paths
                    linux_paths = [
                        call
                        for call in calls
                        if any(
                            path in call
                            for path in [
                                "/usr/bin",
                                "/usr/local/bin",
                                "/opt",
                                "flatpak",
                                "snap",
                            ]
                        )
                    ]
                    assert len(linux_paths) > 0, "Should check Linux-specific paths"

                elif system == "Windows":
                    # Should check Windows paths
                    windows_paths = [
                        call
                        for call in calls
                        if any(
                            path in call
                            for path in ["Program Files", "AppData", ".exe"]
                        )
                    ]
                    assert len(windows_paths) > 0, "Should check Windows-specific paths"

                elif system == "Darwin":
                    # Should check macOS paths
                    macos_paths = [
                        call
                        for call in calls
                        if any(
                            path in call
                            for path in [
                                "Applications",
                                "Dangerzone.app",
                                "homebrew",
                                "usr/local",
                            ]
                        )
                    ]
                    assert len(macos_paths) > 0, "Should check macOS-specific paths"

    def test_dangerzone_cli_found_simulation(self):
        """Test behavior when Dangerzone CLI is found."""
        mock_path = Path("/mock/dangerzone-cli")

        with patch("defuse.cli.shutil.which", return_value=str(mock_path)):
            result = find_dangerzone_cli()
            assert result == mock_path

    def test_dangerzone_cli_not_found(self):
        """Test behavior when Dangerzone CLI is not found anywhere."""
        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists", return_value=False):
                result = find_dangerzone_cli()
                assert result is None


@pytest.mark.linux
class TestLinuxSanitizerIntegration:
    """Test sanitizer functionality specific to Linux."""

    def test_linux_dangerzone_paths(self):
        """Test Linux-specific Dangerzone detection paths."""
        expected_paths = [
            "/usr/bin/dangerzone-cli",
            "/usr/local/bin/dangerzone-cli",
            "/opt/dangerzone/dangerzone-cli",
            "/snap/dangerzone/current/bin/dangerzone-cli",
        ]

        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:
                mock_exists.return_value = False

                find_dangerzone_cli()

                # Verify Linux paths were checked
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                for expected_path in expected_paths:
                    matching_calls = [call for call in calls if expected_path in call]
                    assert len(matching_calls) > 0, f"Should check {expected_path}"

    def test_linux_sanitizer_initialization(self, temp_dir):
        """Test sanitizer initialization on Linux."""
        config = SanitizerConfig(output_dir=temp_dir / "output")

        with patch(
            "defuse.cli.find_dangerzone_cli",
            return_value=Path("/usr/bin/dangerzone-cli"),
        ):
            sanitizer = DocumentSanitizer(config)
            assert sanitizer.dangerzone_cli == Path("/usr/bin/dangerzone-cli")


@pytest.mark.windows
class TestWindowsSanitizerIntegration:
    """Test sanitizer functionality specific to Windows."""

    def test_windows_dangerzone_paths(self):
        """Test Windows-specific Dangerzone detection paths."""
        expected_paths = [
            "Program Files/Dangerzone/dangerzone-cli.exe",
            "Program Files (x86)/Dangerzone/dangerzone-cli.exe",
            "AppData/Local/Dangerzone/dangerzone-cli.exe",
            "AppData/Roaming/Dangerzone/dangerzone-cli.exe",
        ]

        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:
                mock_exists.return_value = False

                find_dangerzone_cli()

                # Verify Windows paths were checked
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                for expected_path in expected_paths:
                    matching_calls = [call for call in calls if expected_path in call]
                    assert len(matching_calls) > 0, (
                        f"Should check path containing {expected_path}"
                    )

    def test_windows_exe_extension_handling(self):
        """Test that Windows paths properly include .exe extension."""
        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:
                mock_exists.return_value = False

                find_dangerzone_cli()

                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                exe_calls = [call for call in calls if call.endswith(".exe")]
                assert len(exe_calls) > 0, "Should check .exe paths on Windows"

    def test_windows_sanitizer_initialization(self, temp_dir):
        """Test sanitizer initialization on Windows."""
        config = SanitizerConfig(output_dir=temp_dir / "output")

        mock_path = Path("C:/Program Files/Dangerzone/dangerzone-cli.exe")
        with patch("defuse.cli.find_dangerzone_cli", return_value=mock_path):
            sanitizer = DocumentSanitizer(config)
            assert sanitizer.dangerzone_cli == mock_path


@pytest.mark.macos
class TestMacOSSanitizerIntegration:
    """Test sanitizer functionality specific to macOS."""

    def test_macos_app_bundle_paths(self):
        """Test macOS app bundle detection paths."""
        expected_paths = [
            "/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli",
            "~/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli",
        ]

        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:
                mock_exists.return_value = False

                find_dangerzone_cli()

                # Verify macOS app bundle paths were checked
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                for expected_path in expected_paths:
                    # Check for app bundle structure
                    app_bundle_calls = [
                        call
                        for call in calls
                        if "Dangerzone.app" in call and "Contents/MacOS" in call
                    ]
                    assert len(app_bundle_calls) > 0, "Should check app bundle paths"

    def test_macos_homebrew_paths(self):
        """Test macOS Homebrew detection paths."""
        expected_paths = [
            "/opt/homebrew/bin/dangerzone-cli",  # Apple Silicon
            "/usr/local/bin/dangerzone-cli",  # Intel
        ]

        with patch("defuse.cli.shutil.which", return_value=None):
            with patch("defuse.cli.Path.exists") as mock_exists:
                mock_exists.return_value = False

                find_dangerzone_cli()

                # Verify Homebrew paths were checked
                calls = [str(call[0][0]) for call in mock_exists.call_args_list]
                for expected_path in expected_paths:
                    matching_calls = [call for call in calls if expected_path in call]
                    assert len(matching_calls) > 0, f"Should check {expected_path}"

    def test_macos_sanitizer_initialization(self, temp_dir):
        """Test sanitizer initialization on macOS."""
        config = SanitizerConfig(output_dir=temp_dir / "output")

        mock_path = Path("/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli")
        with patch("defuse.cli.find_dangerzone_cli", return_value=mock_path):
            sanitizer = DocumentSanitizer(config)
            assert sanitizer.dangerzone_cli == mock_path


class TestCrossPlatformSanitization:
    """Test sanitization process across platforms."""

    def test_sanitizer_with_mock_dangerzone(self, temp_dir, sample_pdf_data):
        """Test sanitization process with mocked Dangerzone."""
        input_file = temp_dir / "test.pdf"
        input_file.write_bytes(sample_pdf_data)

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = SanitizerConfig(output_dir=output_dir)

        mock_dangerzone_path = Path("/mock/dangerzone-cli")

        with patch("defuse.cli.find_dangerzone_cli", return_value=mock_dangerzone_path):
            with patch("subprocess.run") as mock_run:
                # Mock successful Dangerzone execution
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_result.stdout = "Document converted successfully"
                mock_result.stderr = ""
                mock_run.return_value = mock_result

                # Mock output file creation
                output_file = output_dir / "test_safe.pdf"
                with patch("pathlib.Path.exists", return_value=True):
                    with patch("pathlib.Path.is_file", return_value=True):
                        sanitizer = DocumentSanitizer(config)
                        result = sanitizer.sanitize(input_file)

                        # Should have called Dangerzone
                        assert mock_run.called
                        cmd_args = mock_run.call_args[0][0]
                        assert str(mock_dangerzone_path) in cmd_args

    def test_sanitizer_error_handling(self, temp_dir, sample_pdf_data):
        """Test sanitizer error handling across platforms."""
        input_file = temp_dir / "test.pdf"
        input_file.write_bytes(sample_pdf_data)

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = SanitizerConfig(output_dir=output_dir)

        # Test when Dangerzone is not found
        with patch("defuse.cli.find_dangerzone_cli", return_value=None):
            sanitizer = DocumentSanitizer(config)

            with pytest.raises(RuntimeError, match="Dangerzone CLI not found"):
                sanitizer.sanitize(input_file)

    def test_platform_specific_temp_dirs(self, temp_dir):
        """Test that temp directories work correctly on each platform."""
        config = SanitizerConfig(output_dir=temp_dir / "output")

        # Should be able to create temp files on any platform
        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            sanitizer = DocumentSanitizer(config)

            # Temp directory should be accessible
            with tempfile.TemporaryDirectory() as temp_subdir:
                temp_path = Path(temp_subdir)
                assert temp_path.exists()
                assert temp_path.is_dir()

    def test_output_validation_cross_platform(self, temp_dir, sample_pdf_data):
        """Test output file validation works on all platforms."""
        input_file = temp_dir / "test.pdf"
        input_file.write_bytes(sample_pdf_data)

        output_dir = temp_dir / "output"
        output_dir.mkdir()

        config = SanitizerConfig(output_dir=output_dir)

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            with patch("subprocess.run") as mock_run:
                mock_result = MagicMock()
                mock_result.returncode = 0
                mock_run.return_value = mock_result

                # Test missing output file
                with patch("pathlib.Path.exists", return_value=False):
                    sanitizer = DocumentSanitizer(config)

                    with pytest.raises(RuntimeError, match="Sanitization failed"):
                        sanitizer.sanitize(input_file)


class TestSanitizerConfigurationPlatforms:
    """Test sanitizer configuration across platforms."""

    def test_output_dir_creation_permissions(self, temp_dir):
        """Test output directory creation with proper permissions."""
        output_dir = temp_dir / "sanitized_output"
        config = SanitizerConfig(output_dir=output_dir)

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            sanitizer = DocumentSanitizer(config)

            # Output directory should be created if it doesn't exist
            assert output_dir.exists()
            assert output_dir.is_dir()

            # Should be writable
            test_file = output_dir / "test_write.txt"
            test_file.write_text("test")
            assert test_file.exists()

    def test_config_validation_cross_platform(self, temp_dir):
        """Test configuration validation works on all platforms."""
        # Test valid config
        valid_config = SanitizerConfig(output_dir=temp_dir / "output")

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            sanitizer = DocumentSanitizer(valid_config)
            assert sanitizer.config == valid_config

        # Test invalid config
        invalid_dir = temp_dir / "nonexistent" / "deeply" / "nested" / "invalid"
        invalid_config = SanitizerConfig(output_dir=invalid_dir)

        with patch(
            "defuse.cli.find_dangerzone_cli", return_value=Path("/mock/dangerzone")
        ):
            # Should create the directory structure
            sanitizer = DocumentSanitizer(invalid_config)
            assert invalid_dir.exists()
