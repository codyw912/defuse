"""
Unit tests for cross-platform resource management.

Tests resource limit setting and retrieval across different platforms.
"""

from unittest.mock import patch, MagicMock

from defuse.resources import (
    ResourceManager,
    ResourceLimits,
    ResourceInfo,
    setup_download_limits,
    get_resource_info,
)


class TestResourceManager:
    """Test ResourceManager functionality."""

    def test_resource_manager_initialization_unix(self):
        """Test ResourceManager initializes correctly on Unix systems."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                # Mock successful resource module import
                mock_resource = MagicMock()
                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()

                    assert manager.supported is True
                    assert manager._resource_module is not None

    def test_resource_manager_initialization_windows(self):
        """Test ResourceManager on Windows (unsupported)."""
        with patch("platform.system", return_value="Windows"):
            with patch("defuse.resources.platform.system", return_value="Windows"):
                manager = ResourceManager()

                assert manager.supported is False
                assert manager._resource_module is None

    def test_resource_manager_import_error(self):
        """Test ResourceManager when resource module is unavailable."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                # Simulate ImportError by making resource unavailable
                import sys

                # Temporarily remove resource module if it exists
                resource_backup = sys.modules.get("resource")
                if "resource" in sys.modules:
                    del sys.modules["resource"]

                try:
                    # Block the import of resource module
                    sys.modules["resource"] = None

                    # Force re-initialization
                    manager = ResourceManager()
                    manager._resource_module = None
                    manager._supported = False
                    manager._initialize()

                    assert manager.supported is False
                finally:
                    # Restore original state
                    if resource_backup is not None:
                        sys.modules["resource"] = resource_backup
                    elif "resource" in sys.modules:
                        del sys.modules["resource"]

    def test_resource_manager_supported_property(self):
        """Test the supported property."""
        manager = ResourceManager()

        # The property should return a boolean
        assert isinstance(manager.supported, bool)

    def test_set_limits_unsupported_platform(self):
        """Test set_limits on unsupported platform."""
        with patch("platform.system", return_value="Windows"):
            with patch("defuse.resources.platform.system", return_value="Windows"):
                manager = ResourceManager()
                limits = ResourceLimits(max_memory_mb=512, max_cpu_seconds=60)

                result = manager.set_limits(limits)

                assert result is False

    def test_set_limits_memory_only(self):
        """Test setting only memory limits."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_AS = 9
                mock_resource.setrlimit = MagicMock()

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()
                    limits = ResourceLimits(max_memory_mb=512)

                    result = manager.set_limits(limits)

                    assert result is True
                    # Verify setrlimit was called with correct memory value
                    mock_resource.setrlimit.assert_called_once()
                    call_args = mock_resource.setrlimit.call_args
                    assert call_args[0][0] == 9  # RLIMIT_AS
                    assert call_args[0][1] == (512 * 1024 * 1024, 512 * 1024 * 1024)

    def test_set_limits_cpu_only(self):
        """Test setting only CPU limits."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_CPU = 0
                mock_resource.setrlimit = MagicMock()

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()
                    limits = ResourceLimits(max_cpu_seconds=60)

                    result = manager.set_limits(limits)

                    assert result is True
                    mock_resource.setrlimit.assert_called_once_with(0, (60, 60))

    def test_set_limits_file_descriptors_only(self):
        """Test setting only file descriptor limits."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_NOFILE = 7
                mock_resource.setrlimit = MagicMock()

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()
                    limits = ResourceLimits(max_file_descriptors=1024)

                    result = manager.set_limits(limits)

                    assert result is True
                    mock_resource.setrlimit.assert_called_once_with(
                        7, (1024, 2048)
                    )  # soft, hard (doubled)

    def test_set_limits_all_parameters(self):
        """Test setting all resource limits together."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_AS = 9
                mock_resource.RLIMIT_CPU = 0
                mock_resource.RLIMIT_NOFILE = 7
                mock_resource.setrlimit = MagicMock()

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()
                    limits = ResourceLimits(
                        max_memory_mb=256, max_cpu_seconds=30, max_file_descriptors=512
                    )

                    result = manager.set_limits(limits)

                    assert result is True
                    # Should be called 3 times (memory, CPU, FD)
                    assert mock_resource.setrlimit.call_count == 3

    def test_set_limits_oserror(self):
        """Test set_limits handles OSError gracefully."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_AS = 9
                mock_resource.setrlimit = MagicMock(
                    side_effect=OSError("Permission denied")
                )

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()
                    limits = ResourceLimits(max_memory_mb=512)

                    result = manager.set_limits(limits)

                    assert result is False

    def test_set_limits_valueerror(self):
        """Test set_limits handles ValueError gracefully."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_CPU = 0
                mock_resource.setrlimit = MagicMock(
                    side_effect=ValueError("Invalid value")
                )

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()
                    limits = ResourceLimits(max_cpu_seconds=60)

                    result = manager.set_limits(limits)

                    assert result is False

    def test_get_current_limits_unsupported(self):
        """Test get_current_limits on unsupported platform."""
        with patch("platform.system", return_value="Windows"):
            with patch("defuse.resources.platform.system", return_value="Windows"):
                manager = ResourceManager()

                info = manager.get_current_limits()

                assert isinstance(info, ResourceInfo)
                assert info.supported is False
                assert info.memory_limit is None
                assert info.cpu_limit is None
                assert info.fd_limit is None

    def test_get_current_limits_success(self):
        """Test get_current_limits on supported platform."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_AS = 9
                mock_resource.RLIMIT_CPU = 0
                mock_resource.RLIMIT_NOFILE = 7
                mock_resource.getrlimit = MagicMock(
                    side_effect=[
                        (1073741824, 1073741824),  # Memory: 1GB
                        (60, 60),  # CPU: 60 seconds
                        (1024, 2048),  # FD: 1024 soft, 2048 hard
                    ]
                )

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()

                    info = manager.get_current_limits()

                    assert info.supported is True
                    assert info.memory_limit == (1073741824, 1073741824)
                    assert info.cpu_limit == (60, 60)
                    assert info.fd_limit == (1024, 2048)

    def test_get_current_limits_oserror(self):
        """Test get_current_limits handles OSError gracefully."""
        with patch("platform.system", return_value="Linux"):
            with patch("defuse.resources.platform.system", return_value="Linux"):
                mock_resource = MagicMock()
                mock_resource.RLIMIT_AS = 9
                mock_resource.getrlimit = MagicMock(
                    side_effect=OSError("Cannot get limits")
                )

                with patch.dict("sys.modules", {"resource": mock_resource}):
                    manager = ResourceManager()

                    info = manager.get_current_limits()

                    assert info.supported is False


class TestConvenienceFunctions:
    """Test convenience functions for resource management."""

    def test_setup_download_limits_default_values(self):
        """Test setup_download_limits with default values."""
        with patch("defuse.resources.resource_manager") as mock_manager:
            mock_manager.set_limits = MagicMock(return_value=True)

            result = setup_download_limits()

            assert result is True
            mock_manager.set_limits.assert_called_once()

            # Check the limits passed
            call_args = mock_manager.set_limits.call_args
            limits = call_args[0][0]
            assert limits.max_memory_mb == 512
            assert limits.max_cpu_seconds == 60
            assert limits.max_file_descriptors == 64

    def test_setup_download_limits_custom_values(self):
        """Test setup_download_limits with custom values."""
        with patch("defuse.resources.resource_manager") as mock_manager:
            mock_manager.set_limits = MagicMock(return_value=True)

            result = setup_download_limits(max_memory_mb=1024, max_cpu_seconds=120)

            assert result is True
            call_args = mock_manager.set_limits.call_args
            limits = call_args[0][0]
            assert limits.max_memory_mb == 1024
            assert limits.max_cpu_seconds == 120

    def test_setup_download_limits_failure(self):
        """Test setup_download_limits when setting limits fails."""
        with patch("defuse.resources.resource_manager") as mock_manager:
            mock_manager.set_limits = MagicMock(return_value=False)

            result = setup_download_limits()

            assert result is False

    def test_get_resource_info_function(self):
        """Test get_resource_info convenience function."""
        with patch("defuse.resources.resource_manager") as mock_manager:
            expected_info = ResourceInfo(
                memory_limit=(1073741824, 1073741824),
                cpu_limit=(60, 60),
                fd_limit=(1024, 2048),
                supported=True,
            )
            mock_manager.get_current_limits = MagicMock(return_value=expected_info)

            info = get_resource_info()

            assert info == expected_info
            assert info.supported is True


class TestResourceLimits:
    """Test ResourceLimits dataclass."""

    def test_resource_limits_default(self):
        """Test ResourceLimits with default values."""
        limits = ResourceLimits()

        assert limits.max_memory_mb is None
        assert limits.max_cpu_seconds is None
        assert limits.max_file_descriptors is None

    def test_resource_limits_partial(self):
        """Test ResourceLimits with partial values."""
        limits = ResourceLimits(max_memory_mb=512)

        assert limits.max_memory_mb == 512
        assert limits.max_cpu_seconds is None
        assert limits.max_file_descriptors is None

    def test_resource_limits_all_values(self):
        """Test ResourceLimits with all values set."""
        limits = ResourceLimits(
            max_memory_mb=1024, max_cpu_seconds=120, max_file_descriptors=2048
        )

        assert limits.max_memory_mb == 1024
        assert limits.max_cpu_seconds == 120
        assert limits.max_file_descriptors == 2048


class TestResourceInfo:
    """Test ResourceInfo dataclass."""

    def test_resource_info_default(self):
        """Test ResourceInfo with default values."""
        info = ResourceInfo()

        assert info.memory_limit is None
        assert info.cpu_limit is None
        assert info.fd_limit is None
        assert info.supported is False

    def test_resource_info_full(self):
        """Test ResourceInfo with all values."""
        info = ResourceInfo(
            memory_limit=(1073741824, 1073741824),
            cpu_limit=(60, 60),
            fd_limit=(1024, 2048),
            supported=True,
        )

        assert info.memory_limit == (1073741824, 1073741824)
        assert info.cpu_limit == (60, 60)
        assert info.fd_limit == (1024, 2048)
        assert info.supported is True
