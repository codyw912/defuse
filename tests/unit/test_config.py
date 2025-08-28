"""
Unit tests for configuration management.
"""

from pathlib import Path

import pytest
import yaml

from defuse.config import (
    Config,
    SandboxConfig,
    SanitizerConfig,
    get_default_config,
    validate_config,
)


@pytest.mark.unit
class TestSandboxConfig:
    """Test the SandboxConfig dataclass."""

    def test_default_sandbox_config(self):
        """Test default sandbox configuration values."""
        config = SandboxConfig()

        assert config.temp_dir == Path("/tmp/pdf-sandbox")
        assert config.max_file_size == 100 * 1024 * 1024  # 100MB
        assert config.download_timeout == 30
        assert config.allowed_domains is None
        assert config.user_agent == "Mozilla/5.0 (compatible; PDF-Sanitizer/1.0)"
        assert config.max_memory_mb == 512
        assert config.max_memory_buffer_mb == 10
        assert config.max_cpu_seconds == 60
        assert config.prefer_memory_download is True
        assert config.enable_certificate_pinning is False
        assert config.isolation_level == "strict"
        assert config.sandbox_backend == "auto"

    def test_custom_sandbox_config(self, temp_dir: Path):
        """Test custom sandbox configuration."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            max_file_size=50 * 1024 * 1024,
            download_timeout=60,
            allowed_domains=["example.com", "trusted.org"],
            max_memory_mb=1024,
            isolation_level="paranoid",
            sandbox_backend="docker",
        )

        assert config.temp_dir == temp_dir
        assert config.max_file_size == 50 * 1024 * 1024
        assert config.download_timeout == 60
        assert config.allowed_domains == ["example.com", "trusted.org"]
        assert config.max_memory_mb == 1024
        assert config.isolation_level == "paranoid"
        assert config.sandbox_backend == "docker"

    def test_sandbox_config_types(self):
        """Test that sandbox config has correct types."""
        config = SandboxConfig()

        assert isinstance(config.temp_dir, Path)
        assert isinstance(config.max_file_size, int)
        assert isinstance(config.download_timeout, int)
        assert isinstance(config.user_agent, str)
        assert isinstance(config.max_memory_mb, int)
        assert isinstance(config.prefer_memory_download, bool)
        assert isinstance(config.isolation_level, str)
        assert isinstance(config.sandbox_backend, str)


@pytest.mark.unit
class TestSanitizerConfig:
    """Test the SanitizerConfig dataclass."""

    def test_default_sanitizer_config(self):
        """Test default sanitizer configuration values."""
        config = SanitizerConfig()

        assert config.output_dir == Path.home() / "Downloads"
        assert config.keep_temp_files is False
        assert config.ocr_lang is None
        assert config.archive_original is False
        assert config.keep_unsafe_files is False

    def test_custom_sanitizer_config(self, temp_dir: Path):
        """Test custom sanitizer configuration."""
        config = SanitizerConfig(
            output_dir=temp_dir,
            keep_temp_files=True,
            ocr_lang="eng",
            archive_original=True,
            keep_unsafe_files=True,
        )

        assert config.output_dir == temp_dir
        assert config.keep_temp_files is True
        assert config.ocr_lang == "eng"
        assert config.archive_original is True
        assert config.keep_unsafe_files is True

    def test_sanitizer_config_types(self):
        """Test that sanitizer config has correct types."""
        config = SanitizerConfig()

        assert isinstance(config.output_dir, Path)
        assert isinstance(config.keep_temp_files, bool)
        assert isinstance(config.archive_original, bool)
        assert isinstance(config.keep_unsafe_files, bool)


@pytest.mark.unit
class TestConfig:
    """Test the main Config class."""

    def test_default_config_initialization(self):
        """Test default config initialization."""
        config = Config()

        assert isinstance(config.sandbox, SandboxConfig)
        assert isinstance(config.sanitizer, SanitizerConfig)
        assert config.verbose is False
        assert config.dangerzone_path is None

    def test_config_directory_creation(self, temp_dir: Path):
        """Test that config creates necessary directories."""
        # Use the default config which creates directories
        config = get_default_config()

        # Verify that default directories are created
        assert config.sandbox.temp_dir.exists()
        assert config.sanitizer.output_dir.exists()

    def test_config_with_dangerzone_path(self, temp_dir: Path):
        """Test config with dangerzone_path set."""
        config = Config()
        dangerzone_path = temp_dir / "dangerzone-cli"

        config.dangerzone_path = dangerzone_path
        assert config.dangerzone_path == dangerzone_path


@pytest.mark.unit
class TestGetDefaultConfig:
    """Test the get_default_config function."""

    def test_get_default_config_returns_config(self):
        """Test that get_default_config returns a Config instance."""
        config = get_default_config()
        assert isinstance(config, Config)

    def test_get_default_config_creates_fresh_instance(self):
        """Test that get_default_config creates fresh instances."""
        config1 = get_default_config()
        config2 = get_default_config()

        # Should be different instances
        assert config1 is not config2

        # But should have same default values
        assert config1.verbose == config2.verbose
        assert config1.sandbox.max_file_size == config2.sandbox.max_file_size


@pytest.mark.unit
class TestValidateConfig:
    """Test the validate_config function."""

    def test_valid_config(self):
        """Test validation of a valid config."""
        config = get_default_config()
        errors = validate_config(config)

        assert isinstance(errors, list)
        assert len(errors) == 0

    def test_invalid_max_file_size(self):
        """Test validation with invalid max_file_size."""
        config = get_default_config()
        config.sandbox.max_file_size = 0

        errors = validate_config(config)
        assert len(errors) > 0
        assert any("Max file size must be positive" in error for error in errors)

    def test_negative_max_file_size(self):
        """Test validation with negative max_file_size."""
        config = get_default_config()
        config.sandbox.max_file_size = -1000

        errors = validate_config(config)
        assert len(errors) > 0
        assert any("Max file size must be positive" in error for error in errors)

    def test_invalid_download_timeout(self):
        """Test validation with invalid download_timeout."""
        config = get_default_config()
        config.sandbox.download_timeout = 0

        errors = validate_config(config)
        assert len(errors) > 0
        assert any("Download timeout must be positive" in error for error in errors)

    def test_negative_download_timeout(self):
        """Test validation with negative download_timeout."""
        config = get_default_config()
        config.sandbox.download_timeout = -30

        errors = validate_config(config)
        assert len(errors) > 0
        assert any("Download timeout must be positive" in error for error in errors)

    def test_multiple_validation_errors(self):
        """Test validation with multiple errors."""
        config = get_default_config()
        config.sandbox.max_file_size = -1000
        config.sandbox.download_timeout = -30

        errors = validate_config(config)
        assert len(errors) == 2
        assert any("Max file size must be positive" in error for error in errors)
        assert any("Download timeout must be positive" in error for error in errors)

    def test_validation_returns_list(self):
        """Test that validation always returns a list."""
        config = get_default_config()
        errors = validate_config(config)

        assert isinstance(errors, list)


@pytest.mark.unit
class TestConfigIntegration:
    """Test integration scenarios with configuration."""

    def test_config_file_structure(self):
        """Test that config structure supports YAML serialization."""
        config = get_default_config()

        # Test that config can be converted to dict-like structure
        config_dict = {
            "sandbox": {
                "temp_dir": str(config.sandbox.temp_dir),
                "max_file_size": config.sandbox.max_file_size,
                "download_timeout": config.sandbox.download_timeout,
                "isolation_level": config.sandbox.isolation_level,
                "sandbox_backend": config.sandbox.sandbox_backend,
            },
            "sanitizer": {
                "output_dir": str(config.sanitizer.output_dir),
                "keep_temp_files": config.sanitizer.keep_temp_files,
            },
            "verbose": config.verbose,
        }

        # Should be serializable to YAML
        yaml_str = yaml.dump(config_dict, default_flow_style=False)
        assert isinstance(yaml_str, str)
        assert "sandbox:" in yaml_str
        assert "sanitizer:" in yaml_str

    def test_config_path_handling(self, temp_dir: Path):
        """Test that config handles Path objects correctly."""
        config = get_default_config()

        # Set custom paths
        custom_temp = temp_dir / "custom_temp"
        custom_output = temp_dir / "custom_output"

        config.sandbox.temp_dir = custom_temp
        config.sanitizer.output_dir = custom_output

        # Paths should remain as Path objects
        assert isinstance(config.sandbox.temp_dir, Path)
        assert isinstance(config.sanitizer.output_dir, Path)
        assert config.sandbox.temp_dir == custom_temp
        assert config.sanitizer.output_dir == custom_output

    def test_config_security_defaults(self):
        """Test that config has secure defaults."""
        config = get_default_config()

        # Security-focused defaults
        assert config.sandbox.prefer_memory_download is True  # Reduces disk exposure
        assert (
            config.sandbox.enable_certificate_pinning is False
        )  # Disabled by default for compatibility
        assert config.sandbox.isolation_level == "strict"  # Good default security
        assert config.sandbox.max_file_size > 0  # Prevents DoS
        assert config.sandbox.download_timeout > 0  # Prevents hang
        assert config.sandbox.max_memory_mb > 0  # Resource limits
        assert config.sanitizer.keep_temp_files is False  # Clean up by default
        assert config.sanitizer.keep_unsafe_files is False  # Don't keep dangerous files

    def test_config_directory_defaults(self):
        """Test that default directories are reasonable."""
        config = get_default_config()

        # Temp directory should be in system temp space
        temp_dir_str = str(config.sandbox.temp_dir)
        # On Windows, paths use backslashes and may start with \tmp
        # On Unix, paths use forward slashes and start with /tmp
        assert temp_dir_str.endswith("pdf-sandbox") or "tmp" in temp_dir_str.lower()

        # Output should be in user's Downloads folder
        assert config.sanitizer.output_dir.name == "Downloads"
        assert str(config.sanitizer.output_dir).endswith("Downloads")

    def test_config_resource_limits_reasonable(self):
        """Test that resource limits are reasonable."""
        config = get_default_config()

        # File size limits
        assert (
            1024 * 1024 <= config.sandbox.max_file_size <= 1024 * 1024 * 1024
        )  # 1MB to 1GB

        # Memory limits
        assert 64 <= config.sandbox.max_memory_mb <= 8192  # 64MB to 8GB
        assert 1 <= config.sandbox.max_memory_buffer_mb <= config.sandbox.max_memory_mb

        # Time limits
        assert 5 <= config.sandbox.download_timeout <= 300  # 5 seconds to 5 minutes
        assert 10 <= config.sandbox.max_cpu_seconds <= 600  # 10 seconds to 10 minutes

    def test_config_backend_options(self):
        """Test that backend configuration options are valid."""
        config = get_default_config()

        valid_isolation_levels = ["none", "basic", "strict", "paranoid"]
        assert config.sandbox.isolation_level in valid_isolation_levels

        valid_backends = ["auto", "firejail", "bubblewrap", "podman", "docker"]
        assert config.sandbox.sandbox_backend in valid_backends


@pytest.mark.unit
class TestConfigEdgeCases:
    """Test edge cases and error conditions."""

    def test_config_with_none_values(self):
        """Test config behavior with None values where allowed."""
        config = Config()

        # These should be allowed to be None
        config.sanitizer.ocr_lang = None
        config.dangerzone_path = None
        config.sandbox.allowed_domains = None

        assert config.sanitizer.ocr_lang is None
        assert config.dangerzone_path is None
        assert config.sandbox.allowed_domains is None

    def test_config_with_empty_allowed_domains(self):
        """Test config with empty allowed_domains list."""
        config = get_default_config()
        config.sandbox.allowed_domains = []

        assert config.sandbox.allowed_domains == []

        # Should still validate
        errors = validate_config(config)
        assert len(errors) == 0

    def test_config_with_very_large_values(self):
        """Test config with very large values."""
        config = get_default_config()

        # Set very large (but still reasonable) values
        config.sandbox.max_file_size = 10 * 1024 * 1024 * 1024  # 10GB
        config.sandbox.download_timeout = 3600  # 1 hour
        config.sandbox.max_memory_mb = 16384  # 16GB

        # Should still validate
        errors = validate_config(config)
        assert len(errors) == 0

    def test_config_immutability_expectations(self):
        """Test config doesn't accidentally share mutable objects."""
        config1 = get_default_config()
        config2 = get_default_config()

        # Modify one config
        config1.sandbox.allowed_domains = ["example.com"]
        config1.verbose = True

        # Other config should not be affected
        assert config2.sandbox.allowed_domains is None
        assert config2.verbose is False
