"""
Command-line interface for Defuse.
"""

import os
import platform
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib.parse import urlparse

import click
import yaml
from tqdm import tqdm

from .config import Config, get_default_config
from .downloader import DocumentDownloadError
from .sandbox import SandboxedDownloader, get_sandbox_capabilities
from .sanitizer import DocumentSanitizeError, DocumentSanitizer
from .resources import get_resource_info


def get_config_dir() -> Path:
    """Get the user configuration directory."""
    if platform.system() == "Darwin":
        return Path.home() / "Library" / "Application Support" / "defuse"
    elif platform.system() == "Windows":
        return Path(os.environ.get("APPDATA", Path.home())) / "defuse"
    else:
        return Path.home() / ".config" / "defuse"


def load_user_config() -> Config:
    """Load user configuration from config file."""
    config_dir = get_config_dir()
    config_file = config_dir / "config.yaml"

    if config_file.exists():
        try:
            with open(config_file, "r") as f:
                user_config = yaml.safe_load(f)

            config = get_default_config()

            # Update config with user settings
            if "dangerzone_path" in user_config:
                config.dangerzone_path = Path(user_config["dangerzone_path"])
            if "output_dir" in user_config:
                config.sanitizer.output_dir = Path(user_config["output_dir"])
            if "allowed_domains" in user_config:
                config.sandbox.allowed_domains = user_config["allowed_domains"]

            return config
        except Exception as e:
            click.echo(f"Warning: Error loading config file: {e}", err=True)

    return get_default_config()


def save_user_config(config: Config):
    """Save user configuration to config file."""
    config_dir = get_config_dir()
    config_dir.mkdir(parents=True, exist_ok=True)
    config_file = config_dir / "config.yaml"

    user_config = {
        "dangerzone_path": str(config.dangerzone_path)
        if hasattr(config, "dangerzone_path")
        else None,
        "output_dir": str(config.sanitizer.output_dir),
        "allowed_domains": config.sandbox.allowed_domains,
    }

    try:
        with open(config_file, "w") as f:
            yaml.dump(user_config, f, default_flow_style=False)
    except Exception as e:
        click.echo(f"Warning: Could not save config: {e}", err=True)


def find_dangerzone_cli() -> Optional[Path]:
    """Find Dangerzone CLI executable."""

    # Check if already in PATH first
    cli_path = shutil.which("dangerzone-cli")
    if cli_path:
        return Path(cli_path)

    # Check environment variable
    env_path = os.environ.get("DANGERZONE_CLI_PATH")
    if env_path:
        path = Path(env_path)
        if path.exists():
            return path

    # Platform-specific search in common installation locations
    system = platform.system()

    if system == "Darwin":
        # macOS: Check inside app bundle (GUI app installation)
        macos_paths = [
            Path("/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"),
            Path(
                "~/Applications/Dangerzone.app/Contents/MacOS/dangerzone-cli"
            ).expanduser(),
            # Homebrew installation -- installs as a cask so it shouldn't be here
            Path("/opt/homebrew/bin/dangerzone-cli"),
            Path("/usr/local/bin/dangerzone-cli"),
        ]
        for path in macos_paths:
            if path.exists():
                return path

    elif system == "Linux":
        # Linux: Check common package manager installation locations
        linux_paths = [
            # Standard locations for package manager installations
            Path("/usr/bin/dangerzone-cli"),
            Path("/usr/local/bin/dangerzone-cli"),
            Path("/bin/dangerzone-cli"),
            # Flatpak installation
            Path("/var/lib/flatpak/exports/bin/dangerzone-cli"),
            Path("~/.local/share/flatpak/exports/bin/dangerzone-cli").expanduser(),
            # Snap installation
            Path("/snap/bin/dangerzone-cli"),
            # AppImage or manual installation in user directories
            Path("~/.local/bin/dangerzone-cli").expanduser(),
            Path("~/bin/dangerzone-cli").expanduser(),
        ]
        for path in linux_paths:
            if path.exists():
                return path

    elif system == "Windows":
        # Windows: Check common installation locations
        windows_paths = [
            # Program Files installations
            Path("C:/Program Files/Dangerzone/dangerzone-cli.exe"),
            Path("C:/Program Files (x86)/Dangerzone/dangerzone-cli.exe"),
            # User-specific installations
            Path.home() / "AppData/Local/Dangerzone/dangerzone-cli.exe",
            Path.home() / "AppData/Roaming/Dangerzone/dangerzone-cli.exe",
        ]
        for path in windows_paths:
            if path.exists():
                return path

    return None


@click.group(invoke_without_command=True)
@click.option("--version", is_flag=True, help="Show version and exit")
@click.pass_context
def main(ctx, version):
    """Defuse - Secure document download and sanitization tool."""
    if version:
        from . import __version__

        click.echo(f"defuse {__version__}")
        return

    if ctx.invoked_subcommand is None:
        click.echo(ctx.get_help())


@main.command()
@click.argument("url")
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for sanitized document",
)
@click.option("--output-filename", "-f", help="Custom filename for output")
@click.option("--keep-original", is_flag=True, help="Keep the original downloaded file")
@click.option(
    "--isolation",
    type=click.Choice(["none", "basic", "strict", "paranoid"]),
    help="Isolation level",
)
@click.option("--memory-only", is_flag=True, help="Force memory-only download")
@click.option(
    "--sandbox-backend",
    type=click.Choice(["auto", "firejail", "bubblewrap", "podman", "docker"]),
    help="Sandbox backend to use (firejail/bubblewrap are experimental)",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def download(
    url,
    output_dir,
    output_filename,
    keep_original,
    isolation,
    memory_only,
    sandbox_backend,
    verbose,
):
    """Download and sanitize a document from a URL."""

    config = load_user_config()

    if output_dir:
        config.sanitizer.output_dir = Path(output_dir)

    if verbose:
        config.verbose = verbose

    # Apply CLI overrides to config
    if isolation:
        config.sandbox.isolation_level = isolation
    if sandbox_backend:
        config.sandbox.sandbox_backend = sandbox_backend
    if memory_only:
        config.sandbox.prefer_memory_download = True

    # Check for Dangerzone
    dangerzone_path = getattr(config, "dangerzone_path", None) or find_dangerzone_cli()
    if not dangerzone_path:
        click.echo("❌ Dangerzone CLI not found!", err=True)
        click.echo("\nTo install Dangerzone:", err=True)
        if platform.system() == "Darwin":
            click.echo("  • Download from: https://dangerzone.rocks", err=True)
            click.echo("  • Or use Homebrew: brew install --cask dangerzone", err=True)
        else:
            click.echo("  • Install from: https://dangerzone.rocks", err=True)
            click.echo("  • Or use your package manager", err=True)
        click.echo("\nThen run: defuse check-deps", err=True)
        sys.exit(1)

    # Assert dangerzone_path is not None for type checker
    assert dangerzone_path is not None

    # Check container runtime availability upfront
    runtime_name, runtime_path, version = check_container_runtime()
    if not runtime_name:
        click.echo("❌ Container runtime not available!", err=True)
        click.echo(
            "Defuse requires Docker or Podman to safely download documents.", err=True
        )
        click.echo(
            "Please install a container runtime and run: defuse check-deps", err=True
        )
        sys.exit(1)

    try:
        # Initialize components
        downloader = SandboxedDownloader(config)
        sanitizer = DocumentSanitizer(config.sanitizer, dangerzone_path)

        click.echo(f"📥 Downloading document from: {url}")

        # Download document
        downloaded_file = downloader.sandboxed_download(url)

        if downloaded_file is None:
            raise DocumentDownloadError("Download failed - all sandbox methods failed")

        if verbose:
            click.echo(f"✓ Downloaded to: {downloaded_file}")

        # Sanitize document
        click.echo("🔄 Sanitizing document with Dangerzone...")

        # Extract original filename from URL if no output filename specified
        if output_filename is None:
            parsed_url = urlparse(url)
            original_filename = (
                Path(parsed_url.path).name if parsed_url.path else "document"
            )
            # Remove any extension and use as base name (Dangerzone outputs PDF)
            base_name = (
                Path(original_filename).stem if original_filename else "document"
            )
            output_filename = f"{base_name}_defused.pdf"

        sanitized_file = sanitizer.sanitize(downloaded_file, output_filename)

        click.echo(f"✅ Sanitized document saved to: {sanitized_file}")

        # Cleanup
        if not keep_original:
            downloaded_file.unlink(missing_ok=True)
            if verbose:
                click.echo("🗑️  Original file cleaned up")

    except DocumentDownloadError as e:
        click.echo(f"❌ Download failed: {e}", err=True)
        sys.exit(1)
    except DocumentSanitizeError as e:
        click.echo(f"❌ Sanitization failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("file_path", type=click.Path(exists=True))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for sanitized document",
)
@click.option("--output-filename", "-f", help="Custom filename for output")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def sanitize(file_path, output_dir, output_filename, verbose):
    """Sanitize a local document file."""

    config = load_user_config()

    if output_dir:
        config.sanitizer.output_dir = Path(output_dir)

    if verbose:
        config.verbose = verbose

    # Check for Dangerzone
    dangerzone_path = getattr(config, "dangerzone_path", None) or find_dangerzone_cli()
    if not dangerzone_path:
        click.echo("❌ Dangerzone CLI not found!", err=True)
        click.echo("Run: defuse check-deps", err=True)
        sys.exit(1)

    # Assert dangerzone_path is not None for type checker
    assert dangerzone_path is not None

    try:
        input_file = Path(file_path)
        sanitizer = DocumentSanitizer(config.sanitizer, dangerzone_path)

        click.echo(f"🔄 Sanitizing: {input_file}")

        # Generate defused filename if not specified
        if output_filename is None:
            base_name = input_file.stem
            output_filename = f"{base_name}_defused.pdf"

        sanitized_file = sanitizer.sanitize(input_file, output_filename)

        click.echo(f"✅ Sanitized document saved to: {sanitized_file}")

    except DocumentSanitizeError as e:
        click.echo(f"❌ Sanitization failed: {e}", err=True)
        sys.exit(1)
    except Exception as e:
        click.echo(f"❌ Unexpected error: {e}", err=True)
        sys.exit(1)


@main.command()
@click.argument("urls_file", type=click.File("r"))
@click.option(
    "--output-dir",
    "-o",
    type=click.Path(),
    help="Output directory for sanitized documents",
)
@click.option("--keep-originals", is_flag=True, help="Keep original downloaded files")
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def batch(urls_file, output_dir, keep_originals, verbose):
    """Process multiple URLs from a file."""

    config = load_user_config()

    if output_dir:
        config.sanitizer.output_dir = Path(output_dir)

    if verbose:
        config.verbose = verbose

    # Check for Dangerzone
    dangerzone_path = getattr(config, "dangerzone_path", None) or find_dangerzone_cli()
    if not dangerzone_path:
        click.echo("❌ Dangerzone CLI not found!", err=True)
        sys.exit(1)

    # Assert dangerzone_path is not None for type checker
    assert dangerzone_path is not None

    # Check container runtime availability upfront
    runtime_name, runtime_path, version = check_container_runtime()
    if not runtime_name:
        click.echo("❌ Container runtime not available!", err=True)
        click.echo(
            "Defuse requires Docker or Podman to safely download documents.", err=True
        )
        click.echo(
            "Please install a container runtime and run: defuse check-deps", err=True
        )
        sys.exit(1)

    # Read URLs
    urls = [
        line.strip() for line in urls_file if line.strip() and not line.startswith("#")
    ]

    if not urls:
        click.echo("No URLs found in file", err=True)
        sys.exit(1)

    # Initialize components
    downloader = SandboxedDownloader(config)
    sanitizer = DocumentSanitizer(config.sanitizer, dangerzone_path)

    success_count = 0

    with tqdm(urls, desc="Processing documents") as pbar:
        for url in pbar:
            pbar.set_description(f"Processing: {url[:50]}...")

            try:
                downloaded_file = downloader.sandboxed_download(url)

                if downloaded_file is None:
                    raise DocumentDownloadError(
                        "Download failed - all sandbox methods failed"
                    )

                # Extract original filename from URL for batch processing
                parsed_url = urlparse(url)
                original_filename = (
                    Path(parsed_url.path).name if parsed_url.path else "document"
                )
                base_name = (
                    Path(original_filename).stem if original_filename else "document"
                )
                output_filename = f"{base_name}_defused.pdf"

                sanitizer.sanitize(downloaded_file, output_filename)

                if not keep_originals:
                    downloaded_file.unlink(missing_ok=True)

                success_count += 1
                pbar.set_postfix(success=success_count)

            except Exception as e:
                if verbose:
                    click.echo(f"\n❌ Failed {url}: {e}", err=True)
                continue

    click.echo(f"\n✅ Successfully processed {success_count}/{len(urls)} documents")


def check_container_runtime():
    """Check for container runtime (Docker/Podman)."""
    # Check Docker first
    docker_path = shutil.which("docker")
    if docker_path:
        try:
            # Test if Docker daemon is running
            result = subprocess.run(
                [docker_path, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return "Docker", docker_path, result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    # Check Podman
    podman_path = shutil.which("podman")
    if podman_path:
        try:
            result = subprocess.run(
                [podman_path, "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=10,
            )
            if result.returncode == 0:
                return "Podman", podman_path, result.stdout.strip()
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return None, None, None


@main.command("check-deps")
def check_deps():
    """Check for required dependencies."""

    click.echo("🔍 Checking dependencies...\n")

    all_good = True

    # Check Dangerzone
    dangerzone_path = find_dangerzone_cli()
    if dangerzone_path:
        click.echo(f"✅ Dangerzone CLI found: {dangerzone_path}")

        # Save to config
        config = load_user_config()
        config.dangerzone_path = dangerzone_path
        save_user_config(config)

    else:
        click.echo("❌ Dangerzone CLI not found")
        click.echo("\nTo install Dangerzone:")
        if platform.system() == "Darwin":
            click.echo("  • Download from: https://dangerzone.rocks")
            click.echo("  • Or use Homebrew: brew install --cask dangerzone")
        else:
            click.echo("  • Install from: https://dangerzone.rocks")
            click.echo("  • Or use your package manager")
        all_good = False

    # Check container runtime
    click.echo()
    runtime_name, runtime_path, version = check_container_runtime()
    if runtime_name:
        click.echo(f"✅ {runtime_name} found: {runtime_path}")
        if version:
            click.echo(f"   Version: {version}")
    else:
        click.echo("❌ No container runtime found (Docker/Podman)")
        click.echo("\nDangerzone requires a container runtime:")
        if platform.system() == "Darwin":
            click.echo(
                "  • Install Docker Desktop: https://docker.com/products/docker-desktop"
            )
            click.echo("  • Or use Homebrew: brew install --cask docker")
        elif platform.system() == "Linux":
            click.echo("  • Docker: https://docs.docker.com/engine/install/")
            click.echo("  • Podman: Use your package manager (podman)")
        else:
            click.echo("  • Docker Desktop: https://docker.com/products/docker-desktop")
        all_good = False

    if all_good:
        click.echo("\n🎉 All dependencies are ready!")
    else:
        click.echo("\n⚠️  Some dependencies are missing. Install them to use defuse.")


@main.command("test-sandbox")
def test_sandbox():
    """Test available sandboxing capabilities."""

    click.echo("🛡️  Testing sandbox capabilities...\n")

    capabilities = get_sandbox_capabilities()

    click.echo(f"Platform: {capabilities.platform.title()}")
    click.echo(f"Recommended backend: {capabilities.recommended_backend.value}")
    click.echo(
        f"Maximum isolation level: {capabilities.get_max_isolation_level().value}"
    )
    click.echo()

    click.echo("Available backends:")
    for backend, available in capabilities.available_backends.items():
        status = "✅" if available else "❌"
        click.echo(f"  {status} {backend.value}")

    # Test memory download
    click.echo("\n📊 Memory download test:")
    try:
        import io
        import tempfile

        # Test BytesIO
        io.BytesIO(b"Test data")  # Test BytesIO creation
        click.echo("  ✅ BytesIO support")

        # Test SpooledTemporaryFile
        with tempfile.SpooledTemporaryFile(max_size=1024) as spool:
            spool.write(b"Test data")
            click.echo("  ✅ SpooledTemporaryFile support")

        click.echo("  ✅ Memory-first downloads available")

    except Exception as e:
        click.echo(f"  ❌ Memory download test failed: {e}")

    # Resource limits test
    click.echo("\n🔒 Resource limits test:")
    resource_info = get_resource_info()

    if not resource_info.supported:
        if platform.system() == "Windows":
            click.echo(
                "  ℹ️ Resource limits not available on Windows (using container limits)"
            )
        else:
            click.echo("  ❌ Resource limits not available on this platform")
    else:
        memory_limit = resource_info.memory_limit
        if memory_limit and memory_limit[0] > 0:
            click.echo(
                f"  ✅ Resource limits supported "
                f"(current memory limit: {memory_limit[0]} bytes)"
            )
        else:
            click.echo("  ✅ Resource limits supported")

    click.echo("\n🎯 Recommendation:")
    if capabilities.get_max_isolation_level().value == "paranoid":
        click.echo("  Your system supports maximum security isolation!")
    elif capabilities.get_max_isolation_level().value == "strict":
        click.echo("  Your system supports good security isolation.")
    else:
        click.echo("  Consider installing firejail or bubblewrap for better isolation.")
        if capabilities.platform == "linux":
            click.echo("    sudo apt install firejail  # Ubuntu/Debian")
            click.echo("    sudo dnf install firejail  # Fedora")


@main.command("security-report")
def security_report():
    """Generate a detailed security report."""

    config = load_user_config()

    # Create a sandboxed downloader to get capabilities
    try:
        sandboxed_downloader = SandboxedDownloader(config)
        security_info = sandboxed_downloader.get_security_report()

        click.echo("🔒 Defuse Security Report\n")

        click.echo(f"Platform: {security_info['platform'].title()}")
        click.echo(
            f"Current isolation level: {security_info['current_isolation_level']}"
        )
        click.echo(f"Current backend: {security_info['current_backend']}")
        click.echo(f"Recommended backend: {security_info['recommended_backend']}")
        click.echo(
            f"Maximum isolation available: {security_info['max_isolation_level']}"
        )
        click.echo()

        click.echo("Available Security Features:")
        for backend, available in security_info["available_backends"].items():
            status = "✅ Enabled" if available else "❌ Not available"
            click.echo(f"  {backend}: {status}")

        click.echo()
        click.echo("Current Configuration:")
        click.echo(
            f"  Memory-first downloads: "
            f"{'✅' if config.sandbox.prefer_memory_download else '❌'}"
        )
        click.echo(f"  Memory buffer limit: {config.sandbox.max_memory_buffer_mb}MB")
        click.echo(
            f"  Maximum file size: {config.sandbox.max_file_size // (1024 * 1024)}MB"
        )
        click.echo(f"  Download timeout: {config.sandbox.download_timeout}s")
        click.echo(f"  Max CPU time: {config.sandbox.max_cpu_seconds}s")
        click.echo(f"  Max memory: {config.sandbox.max_memory_mb}MB")

    except Exception as e:
        click.echo(f"❌ Could not generate security report: {e}")


@main.command()
@click.option(
    "--dangerzone-path", type=click.Path(exists=True), help="Path to dangerzone-cli"
)
@click.option("--output-dir", type=click.Path(), help="Default output directory")
@click.option("--add-domain", help="Add allowed domain")
@click.option("--list", "list_config", is_flag=True, help="List current configuration")
def config(dangerzone_path, output_dir, add_domain, list_config):
    """Configure Defuse settings."""

    user_config = load_user_config()

    if list_config:
        click.echo("Current configuration:")
        click.echo(
            f"  Dangerzone path: {getattr(user_config, 'dangerzone_path', 'Not set')}"
        )
        click.echo(f"  Output directory: {user_config.sanitizer.output_dir}")
        click.echo(
            f"  Allowed domains: {user_config.sandbox.allowed_domains or 'All allowed'}"
        )
        return

    changed = False

    if dangerzone_path:
        user_config.dangerzone_path = Path(dangerzone_path)
        click.echo(f"✓ Dangerzone path set to: {dangerzone_path}")
        changed = True

    if output_dir:
        user_config.sanitizer.output_dir = Path(output_dir)
        click.echo(f"✓ Output directory set to: {output_dir}")
        changed = True

    if add_domain:
        if user_config.sandbox.allowed_domains is None:
            user_config.sandbox.allowed_domains = []
        if add_domain not in user_config.sandbox.allowed_domains:
            user_config.sandbox.allowed_domains.append(add_domain)
            click.echo(f"✓ Added allowed domain: {add_domain}")
            changed = True
        else:
            click.echo(f"Domain already allowed: {add_domain}")

    if changed:
        save_user_config(user_config)
        click.echo("Configuration saved!")
    elif not any([dangerzone_path, output_dir, add_domain]):
        click.echo("Use --help to see configuration options")


if __name__ == "__main__":
    main()
