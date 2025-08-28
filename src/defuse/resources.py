"""
Cross-platform resource management utilities.

This module provides a clean abstraction for setting resource limits
that works across Unix and Windows systems.
"""

import platform
from typing import Optional, Tuple
from dataclasses import dataclass


@dataclass
class ResourceLimits:
    """Resource limit configuration."""

    max_memory_mb: Optional[int] = None
    max_cpu_seconds: Optional[int] = None
    max_file_descriptors: Optional[int] = None


@dataclass
class ResourceInfo:
    """Information about current resource limits."""

    memory_limit: Optional[Tuple[int, int]] = None
    cpu_limit: Optional[Tuple[int, int]] = None
    fd_limit: Optional[Tuple[int, int]] = None
    supported: bool = False


class ResourceManager:
    """Cross-platform resource limit management."""

    def __init__(self):
        self._resource_module = None
        self._supported = False
        self._initialize()

    def _initialize(self):
        """Initialize the resource manager based on platform."""
        if platform.system() == "Windows":
            # Windows doesn't support Unix resource limits
            self._supported = False
            return

        try:
            import resource

            self._resource_module = resource
            self._supported = True
        except ImportError:
            self._supported = False

    @property
    def supported(self) -> bool:
        """Whether resource limits are supported on this platform."""
        return self._supported

    def set_limits(self, limits: ResourceLimits) -> bool:
        """
        Set resource limits.

        Args:
            limits: The resource limits to set

        Returns:
            True if limits were set successfully, False otherwise
        """
        if not self._supported or not self._resource_module:
            return False

        try:
            if limits.max_memory_mb is not None:
                memory_bytes = limits.max_memory_mb * 1024 * 1024
                self._resource_module.setrlimit(
                    self._resource_module.RLIMIT_AS, (memory_bytes, memory_bytes)
                )

            if limits.max_cpu_seconds is not None:
                self._resource_module.setrlimit(
                    self._resource_module.RLIMIT_CPU,
                    (limits.max_cpu_seconds, limits.max_cpu_seconds),
                )

            if limits.max_file_descriptors is not None:
                self._resource_module.setrlimit(
                    self._resource_module.RLIMIT_NOFILE,
                    (limits.max_file_descriptors, limits.max_file_descriptors * 2),
                )

            return True

        except (OSError, ValueError, AttributeError):
            return False

    def get_current_limits(self) -> ResourceInfo:
        """
        Get current resource limits.

        Returns:
            ResourceInfo with current limits and availability
        """
        if not self._supported or not self._resource_module:
            return ResourceInfo(supported=False)

        try:
            memory_limit = self._resource_module.getrlimit(
                self._resource_module.RLIMIT_AS
            )
            cpu_limit = self._resource_module.getrlimit(
                self._resource_module.RLIMIT_CPU
            )
            fd_limit = self._resource_module.getrlimit(
                self._resource_module.RLIMIT_NOFILE
            )

            return ResourceInfo(
                memory_limit=memory_limit,
                cpu_limit=cpu_limit,
                fd_limit=fd_limit,
                supported=True,
            )

        except (OSError, ValueError, AttributeError):
            return ResourceInfo(supported=False)


# Global instance for convenience
resource_manager = ResourceManager()


def setup_download_limits(max_memory_mb: int = 512, max_cpu_seconds: int = 60) -> bool:
    """
    Convenience function to set up standard download resource limits.

    Args:
        max_memory_mb: Maximum memory in MB
        max_cpu_seconds: Maximum CPU time in seconds

    Returns:
        True if limits were set successfully
    """
    limits = ResourceLimits(
        max_memory_mb=max_memory_mb,
        max_cpu_seconds=max_cpu_seconds,
        max_file_descriptors=64,
    )
    return resource_manager.set_limits(limits)


def get_resource_info() -> ResourceInfo:
    """Get current resource information."""
    return resource_manager.get_current_limits()
