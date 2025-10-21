# START HERE - Defuse

👋 **Welcome!** This document tells you everything you need to know to get started.

## Quick Context

Defuse is a secure document download and sanitization tool that uses Dangerzone to convert potentially dangerous documents into safe PDFs. It supports multiple formats (PDFs, Word docs, PowerPoint, images) and provides a CLI for downloading from URLs, sanitizing local files, and batch processing.

**Key Info:**
- **Tech stack**: Python 3.9+, Click (CLI), Requests, PyYAML, Dangerzone (external dependency)
- **Purpose**: Security tool for safely handling untrusted documents with download + sanitization workflow
- **Status**: Beta (v0.1.0) - Active development with cross-platform support (macOS, Linux, Windows)

## Getting Started

### First Time Setup

```bash
# Clone and install with uv
git clone https://github.com/codyw912/defuse
cd defuse

# Sync dependencies (includes dev dependencies)
uv sync --extra dev

# Install Dangerzone (required external dependency)
# macOS: brew install --cask dangerzone
# Linux: Use package manager or download from dangerzone.rocks
# Windows: Download installer from dangerzone.rocks
```

### Running the Project

```bash
# Run the CLI
uv run defuse --help

# Check dependencies are installed
uv run defuse check-deps

# Download and sanitize a document
uv run defuse download https://example.com/document.pdf

# Sanitize a local file
uv run defuse sanitize /path/to/document.pdf

# Run tests
uv run pytest

# Lint code
uv run ruff check
```

## Project Structure

```
defuse/
├── src/defuse/              # Main package
│   ├── cli.py              # Click-based CLI commands
│   ├── config.py           # User configuration management
│   ├── downloader.py       # URL download with security checks
│   ├── formats.py          # File format detection
│   ├── resources.py        # Platform resource paths
│   ├── sandbox.py          # Sandbox backend selection/management
│   └── sanitizer.py        # Dangerzone integration
├── tests/                   # Test suite
│   ├── unit/               # Unit tests for individual modules
│   ├── integration/        # Integration tests (CLI, end-to-end)
│   ├── security/           # Security-focused tests
│   └── fixtures/           # Test fixtures (mock responses, sample files)
├── output/                  # Default output directory for sanitized files
├── pyproject.toml          # Project metadata and dependencies
├── README.md               # User documentation
├── ROADMAP.md              # Future plans and features
├── TESTING_STRATEGY.md     # Testing approach documentation
└── AGENTS.md               # AI agent collaboration guide
```

**Core Modules:**
- `cli.py` - Entry point with commands: download, sanitize, batch, config, check-deps
- `downloader.py` - Secure HTTP downloads with size limits and domain filtering
- `sanitizer.py` - Dangerzone CLI wrapper with format conversion
- `sandbox.py` - Multi-backend sandbox detection (Docker, Podman, Firejail, Bubblewrap)
- `config.py` - YAML-based user configuration (domains, output dirs, Dangerzone path)
- `formats.py` - Magic-byte-based format detection for various document types

## Read These Documents Next

### Current Status
📄 [`../status/current-focus.md`](../status/current-focus.md) - What we're working on now

### Architecture
📄 [`../architecture/overview.md`](../architecture/overview.md) - System architecture

### Documentation Guide
📄 [`../README.md`](../README.md) - How the docs are organized

---

**Ready to code?** Check [`status/current-focus.md`](../status/current-focus.md) for what to work on next! 🚀
