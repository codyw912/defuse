"""
Platform-specific sandboxing and isolation strategies for secure document downloads.
"""

import os
import shutil
import subprocess
import platform
import tempfile
from pathlib import Path
from typing import Optional, List, Dict, Any
from enum import Enum

from .config import Config


class IsolationLevel(Enum):
    """Available isolation levels"""

    NONE = "none"
    BASIC = "basic"  # Resource limits only
    STRICT = "strict"  # Process isolation + sandboxing tools
    PARANOID = "paranoid"  # Maximum isolation available


class SandboxBackend(Enum):
    """Available sandbox backends (prioritizing security)"""

    AUTO = "auto"  # Auto-select best available backend
    FIREJAIL = "firejail"  # Linux sandboxing with fine-grained controls
    BUBBLEWRAP = "bubblewrap"  # Linux unprivileged containers (minimal attack surface)
    PODMAN = "podman"  # Podman container isolation
    DOCKER = "docker"  # Docker container isolation


class SandboxCapabilities:
    """Detected sandbox capabilities for current system"""

    def __init__(self):
        self.platform = platform.system().lower()
        self.available_backends = self._detect_backends()
        self.recommended_backend = self._get_recommended_backend()

    def _detect_backends(self) -> Dict[SandboxBackend, bool]:
        """Detect which sandbox backends are available"""
        capabilities = {
            SandboxBackend.AUTO: True,  # Always available as backend selector
        }

        # Check for Linux-specific sandboxing tools (highest security)
        if self.platform == "linux":
            capabilities[SandboxBackend.FIREJAIL] = shutil.which("firejail") is not None
            capabilities[SandboxBackend.BUBBLEWRAP] = shutil.which("bwrap") is not None
        else:
            capabilities[SandboxBackend.FIREJAIL] = False
            capabilities[SandboxBackend.BUBBLEWRAP] = False

        # Check for container runtimes (cross-platform)
        capabilities[SandboxBackend.DOCKER] = self._check_docker_available()
        capabilities[SandboxBackend.PODMAN] = self._check_podman_available()

        return capabilities

    def _check_docker_available(self) -> bool:
        """Check if Docker is available and running"""
        docker_path = shutil.which("docker")
        if not docker_path:
            return False

        try:
            result = subprocess.run(
                [docker_path, "info"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _check_podman_available(self) -> bool:
        """Check if Podman is available and running"""
        podman_path = shutil.which("podman")
        if not podman_path:
            return False

        try:
            result = subprocess.run(
                [podman_path, "info"], capture_output=True, timeout=5
            )
            return result.returncode == 0
        except (subprocess.TimeoutExpired, FileNotFoundError):
            return False

    def _get_recommended_backend(self) -> SandboxBackend:
        """Get recommended backend prioritizing security (defense in depth with Dangerzone)"""
        # Priority order: specialized Linux sandboxes > container runtimes
        if self.available_backends.get(SandboxBackend.FIREJAIL, False):
            return SandboxBackend.FIREJAIL
        elif self.available_backends.get(SandboxBackend.BUBBLEWRAP, False):
            return SandboxBackend.BUBBLEWRAP
        elif self.platform == "linux" and self.available_backends.get(
            SandboxBackend.PODMAN, False
        ):
            return SandboxBackend.PODMAN  # Podman preferred on Linux
        elif self.available_backends.get(SandboxBackend.DOCKER, False):
            return SandboxBackend.DOCKER
        else:
            raise RuntimeError(
                "No suitable sandboxing backend available. Docker/Podman is required (same as Dangerzone)."
            )

    def get_max_isolation_level(self) -> IsolationLevel:
        """Get maximum isolation level possible on this system"""
        if (
            self.available_backends[SandboxBackend.FIREJAIL]
            or self.available_backends[SandboxBackend.BUBBLEWRAP]
        ):
            return (
                IsolationLevel.PARANOID
            )  # Specialized Linux sandboxes provide maximum isolation
        elif (
            self.available_backends[SandboxBackend.DOCKER]
            or self.available_backends[SandboxBackend.PODMAN]
        ):
            return IsolationLevel.STRICT  # Container runtimes provide good isolation
        else:
            return IsolationLevel.BASIC  # Subprocess isolation as fallback


class SandboxedDownloader:
    """Sandboxed downloader that uses various isolation strategies"""

    def __init__(self, config: Config):
        self.config = config
        self.capabilities = SandboxCapabilities()
        isolation_str = getattr(config.sandbox, "isolation_level", "paranoid")

        # Find enum by value
        self.isolation_level = IsolationLevel.PARANOID  # Default
        for level in IsolationLevel:
            if level.value == isolation_str:
                self.isolation_level = level
                break
        backend_str = getattr(config.sandbox, "sandbox_backend", "auto")

        # Find enum by value
        self.backend = SandboxBackend.AUTO  # Default
        for backend in SandboxBackend:
            if backend.value == backend_str:
                self.backend = backend
                break

        # Auto-select best backend if set to auto
        if self.backend == SandboxBackend.AUTO:
            self.backend = self.capabilities.recommended_backend

    def create_download_script(self, url: str, output_path: Path) -> Path:
        """Create a temporary Python script for isolated download"""
        script_content = f'''
import sys
import io
import os
import tempfile
import urllib.parse
import resource
import signal
from pathlib import Path
import requests

class ContainerDownloadError(Exception):
    pass

def setup_resource_limits():
    """Set up resource limits for the download process"""
    try:
        # Limit virtual memory
        max_memory = {self.config.sandbox.max_memory_mb} * 1024 * 1024
        resource.setrlimit(resource.RLIMIT_AS, (max_memory, max_memory))
        
        # Limit CPU time
        max_cpu_time = {self.config.sandbox.max_cpu_seconds}
        resource.setrlimit(resource.RLIMIT_CPU, (max_cpu_time, max_cpu_time))
        
        # Limit file descriptors
        resource.setrlimit(resource.RLIMIT_NOFILE, (64, 128))
    except (OSError, ValueError):
        # Resource limits may fail, continue without them
        pass

def validate_url(url):
    """Basic URL validation"""
    parsed = urllib.parse.urlparse(url)
    if not parsed.scheme or not parsed.netloc:
        return False
    if parsed.scheme not in ['http', 'https']:
        return False
    # Add domain validation if needed
    allowed_domains = {self.config.sandbox.allowed_domains}
    if allowed_domains:
        if not any(parsed.netloc.endswith(domain) for domain in allowed_domains):
            return False
    return True

def download_to_memory(session, url, max_memory_size):
    """Download to memory with automatic spillover to disk"""
    response = session.get(url, timeout={self.config.sandbox.download_timeout}, stream=True)
    response.raise_for_status()
    
    # Check content length
    content_length = int(response.headers.get('content-length', 0))
    if content_length > {self.config.sandbox.max_file_size}:
        raise ContainerDownloadError(f"File too large: {{content_length}} bytes")
    
    # Use SpooledTemporaryFile for memory-first strategy
    buffer = tempfile.SpooledTemporaryFile(max_size=max_memory_size, mode='w+b')
    downloaded = 0
    
    # Progress tracking
    for chunk in response.iter_content(chunk_size=8192):
        if chunk:
            downloaded += len(chunk)
            if downloaded > {self.config.sandbox.max_file_size}:
                raise ContainerDownloadError("File size exceeded during download")
            buffer.write(chunk)
            
            # Basic progress output every MB
            if downloaded % (1024*1024) == 0:
                print(f"Downloaded: {{downloaded // (1024*1024)}}MB", file=sys.stderr)
    
    buffer.seek(0)
    return buffer

def download_document(url, output_path):
    """Main download function with full security features"""
    try:
        setup_resource_limits()
        
        if not validate_url(url):
            raise ContainerDownloadError(f"Invalid or restricted URL: {{url}}")
        
        # Setup session with proper headers
        session = requests.Session()
        session.headers.update({{
            'User-Agent': '{self.config.sandbox.user_agent}',
            'Accept': '*/*',
        }})
        
        # Memory-first download strategy
        max_memory_size = {self.config.sandbox.max_memory_buffer_mb} * 1024 * 1024
        memory_buffer = download_to_memory(session, url, max_memory_size)
        
        # Save buffer to output file
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            while True:
                chunk = memory_buffer.read(8192)
                if not chunk:
                    break
                f.write(chunk)
        
        memory_buffer.close()
        print(f"SUCCESS: Downloaded to {{output_path}}")
        
    except Exception as e:
        print(f"ERROR: {{str(e)}}")
        sys.exit(1)

if __name__ == "__main__":
    download_document("{url}", "{output_path}")
'''

        # Create temporary script
        script_fd, script_path = tempfile.mkstemp(suffix=".py", text=True)
        try:
            with os.fdopen(script_fd, "w") as f:
                f.write(script_content)
        except:
            os.close(script_fd)
            raise

        return Path(script_path)

    def run_firejail_download(self, url: str, output_path: Path) -> bool:
        """Run download using Firejail sandbox"""
        script_path = self.create_download_script(url, output_path)

        try:
            cmd = [
                "firejail",
                "--noprofile",  # Don't use application profiles
                "--net=none",  # No network access after initial setup
                "--seccomp",  # Enable seccomp filtering
                "--noroot",  # Don't allow root access
                "--private-tmp",  # Private tmp directory
                "--private-dev",  # Private /dev directory
                f"--rlimit-fsize={self.config.sandbox.max_file_size}",  # File size limit
                "--rlimit-nofile=64",  # File descriptor limit
                "--rlimit-nproc=10",  # Process limit
                "--timeout=120",  # Timeout after 2 minutes
                "python3",
                str(script_path),
            ]

            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=150,  # Slightly longer than firejail timeout
            )

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"Firejail download failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("Firejail download timed out")
            return False
        except Exception as e:
            print(f"Firejail error: {str(e)}")
            return False
        finally:
            script_path.unlink(missing_ok=True)

    def run_bubblewrap_download(self, url: str, output_path: Path) -> bool:
        """Run download using Bubblewrap sandbox"""
        script_path = self.create_download_script(url, output_path)

        try:
            cmd = [
                "bwrap",
                "--new-session",
                "--die-with-parent",
                "--unshare-pid",
                "--unshare-net",  # No network access
                "--tmpfs",
                "/tmp",
                "--proc",
                "/proc",
                "--bind",
                "/usr",
                "/usr",
                "--bind",
                "/bin",
                "/bin",
                "--bind",
                "/lib",
                "/lib",
                "--bind",
                "/lib64",
                "/lib64",
                "--ro-bind",
                str(script_path),
                "/tmp/download_script.py",
                "--bind",
                str(output_path.parent),
                "/output",
                "python3",
                "/tmp/download_script.py",
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"Bubblewrap download failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("Bubblewrap download timed out")
            return False
        except Exception as e:
            print(f"Bubblewrap error: {str(e)}")
            return False
        finally:
            script_path.unlink(missing_ok=True)

    def run_docker_download(self, url: str, output_path: Path) -> bool:
        """Run download using Docker container"""

        try:
            # Container output path
            container_output = f"/output/{output_path.name}"

            # Build download command with inline Python script
            download_cmd = f"""
python3 -c "
import sys
import io
import urllib.request
import urllib.error
from pathlib import Path

url = '{url}'
output_path = '{container_output}'
max_size = {self.config.sandbox.max_file_size}

try:
    # Download with size limit
    with urllib.request.urlopen(url, timeout={self.config.sandbox.download_timeout}) as response:
        if hasattr(response, 'length') and response.length and response.length > max_size:
            raise Exception(f'File too large: {{response.length}} bytes')
        
        data = response.read(max_size + 1)
        if len(data) > max_size:
            raise Exception(f'File too large: {{len(data)}} bytes')
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(data)
        
        print(f'SUCCESS: Downloaded {{len(data)}} bytes to {{output_path}}')

except Exception as e:
    print(f'ERROR: {{str(e)}}')
    sys.exit(1)
"
"""

            cmd = [
                "docker",
                "run",
                "--rm",  # Remove container when done
                "--network",
                "bridge",  # Network access for download
                "--memory",
                f"{self.config.sandbox.max_memory_mb}m",  # Memory limit
                "--cpu-shares",
                "512",  # Limited CPU
                "--security-opt",
                "no-new-privileges:true",  # No privilege escalation
                "--read-only",  # Read-only filesystem
                "--tmpfs",
                "/tmp:noexec,nosuid,size=100m",  # Temp space
                "--volume",
                f"{output_path.parent}:/output:rw",  # Output directory
                "python:3.11-slim",
                "sh",
                "-c",
                download_cmd,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=150)

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"Docker download failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("Docker download timed out")
            return False
        except Exception as e:
            print(f"Docker error: {str(e)}")
            return False

    def run_podman_download(self, url: str, output_path: Path) -> bool:
        """Run download using Podman container"""

        try:
            # Container output path
            container_output = f"/output/{output_path.name}"

            # Build download command with inline Python script
            download_cmd = f"""
python3 -c "
import sys
import io
import urllib.request
import urllib.error
from pathlib import Path

url = '{url}'
output_path = '{container_output}'
max_size = {self.config.sandbox.max_file_size}

try:
    # Download with size limit
    with urllib.request.urlopen(url, timeout={self.config.sandbox.download_timeout}) as response:
        if hasattr(response, 'length') and response.length and response.length > max_size:
            raise Exception(f'File too large: {{response.length}} bytes')
        
        data = response.read(max_size + 1)
        if len(data) > max_size:
            raise Exception(f'File too large: {{len(data)}} bytes')
        
        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'wb') as f:
            f.write(data)
        
        print(f'SUCCESS: Downloaded {{len(data)}} bytes to {{output_path}}')

except Exception as e:
    print(f'ERROR: {{str(e)}}')
    sys.exit(1)
"
"""

            cmd = [
                "podman",
                "run",
                "--rm",  # Remove container when done
                "--network",
                "bridge",  # Network access for download
                "--memory",
                f"{self.config.sandbox.max_memory_mb}m",  # Memory limit
                "--cpus",
                "0.5",  # Limited CPU
                "--security-opt",
                "no-new-privileges:true",  # No privilege escalation
                "--read-only",  # Read-only filesystem
                "--tmpfs",
                "/tmp:noexec,nosuid,size=100m",  # Temp space
                "--volume",
                f"{output_path.parent}:/output:rw",  # Output directory
                "python:3.11-slim",
                "sh",
                "-c",
                download_cmd,
            ]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=150)

            if result.returncode == 0 and output_path.exists():
                return True
            else:
                print(f"Podman download failed: {result.stderr}")
                return False

        except subprocess.TimeoutExpired:
            print("Podman download timed out")
            return False
        except Exception as e:
            print(f"Podman error: {str(e)}")
            return False

    def sandboxed_download(
        self, url: str, output_path: Optional[Path] = None
    ) -> Optional[Path]:
        """Perform a sandboxed download using the best available method"""

        # Prepare output path
        if output_path is None:
            temp_file = tempfile.NamedTemporaryFile(
                dir=self.config.sandbox.temp_dir, suffix=".tmp", delete=False
            )
            output_path = Path(temp_file.name)
            temp_file.close()

        # Try the selected backend first
        if (
            self.backend == SandboxBackend.FIREJAIL
            and self.capabilities.available_backends[SandboxBackend.FIREJAIL]
        ):
            if self.run_firejail_download(url, output_path):
                return output_path

        elif (
            self.backend == SandboxBackend.BUBBLEWRAP
            and self.capabilities.available_backends[SandboxBackend.BUBBLEWRAP]
        ):
            if self.run_bubblewrap_download(url, output_path):
                return output_path

        elif (
            self.backend == SandboxBackend.PODMAN
            and self.capabilities.available_backends[SandboxBackend.PODMAN]
        ):
            if self.run_podman_download(url, output_path):
                return output_path

        elif (
            self.backend == SandboxBackend.DOCKER
            and self.capabilities.available_backends[SandboxBackend.DOCKER]
        ):
            if self.run_docker_download(url, output_path):
                return output_path

        # Fallback: try other available backends in security priority order
        fallback_order = [
            SandboxBackend.FIREJAIL,
            SandboxBackend.BUBBLEWRAP,
            SandboxBackend.PODMAN,
            SandboxBackend.DOCKER,
        ]

        for fallback_backend in fallback_order:
            if (
                fallback_backend != self.backend
                and self.capabilities.available_backends.get(fallback_backend, False)
            ):
                if fallback_backend == SandboxBackend.FIREJAIL:
                    if self.run_firejail_download(url, output_path):
                        return output_path
                elif fallback_backend == SandboxBackend.BUBBLEWRAP:
                    if self.run_bubblewrap_download(url, output_path):
                        return output_path
                elif fallback_backend == SandboxBackend.PODMAN:
                    if self.run_podman_download(url, output_path):
                        return output_path
                elif fallback_backend == SandboxBackend.DOCKER:
                    if self.run_docker_download(url, output_path):
                        return output_path

        # All methods failed
        if output_path.exists():
            output_path.unlink(missing_ok=True)
        return None

    def get_security_report(self) -> Dict[str, Any]:
        """Get a report of available security features"""
        return {
            "platform": self.capabilities.platform,
            "available_backends": {
                backend.value: available
                for backend, available in self.capabilities.available_backends.items()
            },
            "recommended_backend": self.capabilities.recommended_backend.value,
            "max_isolation_level": self.capabilities.get_max_isolation_level().value,
            "current_backend": self.backend.value,
            "current_isolation_level": self.isolation_level.value
            if hasattr(self.isolation_level, "value")
            else str(self.isolation_level),
        }


def get_sandbox_capabilities() -> SandboxCapabilities:
    """Get sandbox capabilities for current system"""
    return SandboxCapabilities()


def create_sandboxed_downloader(config: Config) -> SandboxedDownloader:
    """Create a sandboxed downloader with given configuration"""
    return SandboxedDownloader(config)
