# Changelog

All notable changes to Defuse will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.1.0] - 2025-10-21

### Initial Beta Release

First public release of Defuse - a secure document download and sanitization tool.

### Added

#### Core Features
- **Multi-format document support**: PDF, Word (DOC/DOCX), PowerPoint (PPT/PPTX), Excel (XLS/XLSX), images (PNG, JPEG, GIF, TIFF), EPUB, and more
- **Container-based download isolation**: Downloads run in Docker or Podman containers with security constraints
- **Automatic sanitization**: Integration with Dangerzone for converting documents to safe PDFs
- **Cross-platform support**: Works on Linux, macOS, and Windows
- **Batch processing**: Process multiple URLs from a file
- **Security-first architecture**: Defense-in-depth with isolated downloads + Dangerzone sanitization

#### CLI Commands
- `defuse download <url>` - Download and sanitize a document from a URL
- `defuse sanitize <file>` - Sanitize a local document
- `defuse batch <file>` - Process multiple URLs from a file
- `defuse config` - Manage configuration (output dir, domains, Dangerzone path)
- `defuse check-deps` - Verify Docker/Podman and Dangerzone are installed
- `defuse security-report` - Display available security features
- `defuse test-sandbox` - Test sandbox backend capabilities

#### Security Features
- **Container isolation**: Downloads run with no-new-privileges, read-only filesystem, and resource limits
- **URL validation**: HTTP/HTTPS only with optional domain allowlist
- **File size limits**: Configurable maximum file size (default 100MB)
- **Resource limits**: Memory, CPU, and timeout constraints
- **Format detection**: Magic byte verification before processing
- **Adaptive sandboxing**: Automatic selection of best available backend (Docker, Podman, Firejail, Bubblewrap)

#### User Experience
- **Smart defaults**: Outputs to ~/Downloads, preserves original filenames with `_defused` suffix
- **Progress tracking**: Visual progress bars for downloads and sanitization
- **Verbose mode**: Detailed output for debugging (`--verbose` flag)
- **Cross-platform paths**: Automatic detection of Dangerzone and config directories
- **Helpful error messages**: Clear guidance when dependencies are missing

#### Configuration
- **YAML-based config**: User configuration stored in platform-appropriate locations
- **Domain allowlist**: Restrict downloads to specific domains
- **Custom output directory**: Configure default output location
- **Dangerzone path**: Override auto-detection if needed
- **Resource limits**: Configure memory, CPU, file size, and timeout limits

#### Testing & CI
- **90% test coverage**: 456 automated tests covering unit, integration, and security scenarios
- **Security test suite**: Comprehensive tests for container isolation, resource limits, and URL validation
- **GitHub Actions CI**: Automated testing on Linux, macOS, Windows with Python 3.9-3.13
- **Platform-specific testing**: Separate test jobs for Linux sandboxes and security verification

#### Documentation
- **Comprehensive README**: Installation, usage, troubleshooting, and examples
- **Troubleshooting guide**: Common issues for Docker, Dangerzone, and downloads
- **Developer documentation**: AGENTS.md, TESTING_STRATEGY.md, context/ folder
- **Security documentation**: Clear explanation of isolation and defense-in-depth

### Security

#### Container Security
- Docker/Podman containers run with `--security-opt no-new-privileges:true`
- Read-only filesystem (`--read-only`) with tmpfs for temporary files
- tmpfs mounted with `noexec,nosuid` flags
- Memory limits enforced (`--memory` flag)
- CPU shares limited (`--cpu-shares` or `--cpus`)
- Network isolated with bridge mode (allows downloads)
- Containers automatically removed after completion (`--rm`)

#### Download Security
- URL scheme validation (HTTP/HTTPS only)
- Optional domain allowlist enforcement
- File size limits during download
- Memory-first download strategy with disk spillover
- Timeout enforcement for network operations
- Format verification using magic bytes

#### Sandbox Backends
- **Docker** (recommended): Most widely tested, works on all platforms
- **Podman** (alternative): Rootless option, good for Linux
- **Firejail** (experimental): Linux-only, fine-grained sandboxing
- **Bubblewrap** (experimental): Linux-only, unprivileged containers

### Dependencies

#### Required
- Python 3.9 or higher
- Docker or Podman
- Dangerzone (for document sanitization)

#### Python Packages
- click (CLI framework)
- requests (HTTP downloads)
- tqdm (progress bars)
- pyyaml (configuration)

### Known Limitations

1. **Container progress reporting**: Downloads in containers have limited progress visibility (being documented)
2. **First run delay**: Initial container startup downloads Python image (~200MB)
3. **Firejail/Bubblewrap experimental**: Linux sandbox backends may not work in all environments (CI, nested containers)
4. **Large file performance**: Very large files (>500MB) may be slow due to container overhead
5. **Windows testing**: While CI tests Windows, manual testing is limited

### Platform Support

- **Linux**: Full support (Docker, Podman, Firejail, Bubblewrap)
- **macOS**: Full support (Docker, Podman)
- **Windows**: Full support (Docker only)

### Technical Details

- **Package name**: defuse
- **CLI command**: `defuse`
- **License**: MIT
- **Repository**: https://github.com/codyw912/defuse
- **Python support**: 3.9, 3.10, 3.11, 3.12, 3.13
- **Config locations**:
  - Linux: `~/.config/defuse/config.yaml`
  - macOS: `~/Library/Application Support/defuse/config.yaml`
  - Windows: `%APPDATA%\defuse\config.yaml`

### Credits

- Built with Python, Click, and uv
- Sanitization powered by [Dangerzone](https://dangerzone.rocks)
- Inspired by security best practices from Freedom of the Press Foundation

### What's Next (v0.2.0)

Planned features for future releases:
- Enhanced progress reporting from containers
- Performance optimizations (container startup, parallel processing)
- Additional format support (ZIP archives, HTML)
- API server mode
- Browser extension integration
- Windows native sandbox support

---

## [Unreleased]

Changes not yet released will appear here.

[0.1.0]: https://github.com/codyw912/defuse/releases/tag/v0.1.0
