# Defuse

Secure document download and sanitization tool using Dangerzone.

## Overview

Defuse provides a secure way to download documents from the web and sanitize them using [Dangerzone](https://dangerzone.rocks). It supports multiple document formats (PDFs, Word docs, PowerPoint, images, and more) and converts them to safe PDFs while removing potentially malicious content.

## Features

- **Multi-Format Support**: Supports PDFs, Word documents, PowerPoint presentations, images, and other formats supported by Dangerzone
- **Secure Downloads**: Downloads documents with validation, size limits, and domain filtering
- **Automatic Sanitization**: Uses Dangerzone to remove JavaScript, macros, forms, and other potentially dangerous content
- **Batch Processing**: Process multiple URLs from a file
- **Cross-Platform**: Works on macOS, Linux, and Windows
- **Configuration**: Customizable settings for domains, output directories, and more

## Installation

### Install as a uv tool (recommended)

```bash
uv tool install defuse
```

### Install from source

```bash
git clone https://github.com/codyw912/defuse
cd defuse
uv tool install .
```

## Prerequisites

Defuse requires [Dangerzone](https://dangerzone.rocks) to be installed. Defuse will automatically detect Dangerzone in common installation locations on all platforms (PATH, app bundles, package managers, etc.):

### macOS

```bash
# Option 1: Download from website
# https://dangerzone.rocks

# Option 2: Use Homebrew
brew install --cask dangerzone
```

### Linux

```bash
# Use your package manager or download from:
# https://dangerzone.rocks
```

## Usage

### Check Dependencies

```bash
defuse check-deps
```

### Download and Sanitize a Document

```bash
defuse download https://example.com/document.pdf
# Also works with other formats:
defuse download https://example.com/presentation.pptx
defuse download https://example.com/document.docx
```

### Sanitize a Local Document

```bash
defuse sanitize /path/to/document.pdf
# Also works with other formats:
defuse sanitize /path/to/presentation.pptx
defuse sanitize /path/to/document.docx
```

### Batch Process Multiple URLs

```bash
# Create a file with URLs (one per line) - mix of formats supported
echo "https://example.com/doc1.pdf" > urls.txt
echo "https://example.com/presentation.pptx" >> urls.txt
echo "https://example.com/document.docx" >> urls.txt

defuse batch urls.txt
```

### Configuration

```bash
# List current settings
defuse config --list

# Set custom output directory
defuse config --output-dir ~/SafeDocuments

# Add allowed domain
defuse config --add-domain example.com

# Set custom Dangerzone path (only needed if auto-detection fails)
defuse config --dangerzone-path /custom/path/to/dangerzone-cli
```

## Command Options

### `download`

- `--output-dir, -o`: Output directory for sanitized document
- `--output-filename, -f`: Custom filename for output
- `--keep-original`: Keep the original downloaded file
- `--verbose, -v`: Verbose output

### `sanitize`

- `--output-dir, -o`: Output directory for sanitized document
- `--output-filename, -f`: Custom filename for output
- `--verbose, -v`: Verbose output

### `batch`

- `--output-dir, -o`: Output directory for sanitized documents
- `--keep-originals`: Keep original downloaded files
- `--verbose, -v`: Verbose output

## Security Features

- **URL Validation**: Checks URL format and optional domain restrictions
- **File Size Limits**: Prevents downloading excessively large files
- **Format Detection**: Automatically detects document format using magic bytes
- **Defense in Depth**: Layered security with download isolation + Dangerzone's container-based sanitization
- **Adaptive Sandboxing**: Automatically selects the best available sandbox backend:
  - **Linux**: Firejail or Bubblewrap (maximum isolation) > Podman > Docker > subprocess fallback
  - **macOS/Windows**: Docker > Podman > subprocess fallback

## Configuration

Defuse stores user configuration in:

- macOS: `~/Library/Application Support/defuse/config.yaml`
- Linux: `~/.config/defuse/config.yaml`
- Windows: `%APPDATA%/defuse/config.yaml`

## How Dangerzone Works

Dangerzone converts potentially dangerous documents into safe PDFs by:

1. Converting the document into pixel data inside a sandbox (supports PDFs, Word docs, PowerPoint, images, etc.)
2. Using OCR to preserve any text content
3. Reconstructing a clean PDF outside the sandbox
4. Removing all potentially malicious content (JavaScript, macros, forms, embedded files, etc.)

## Development

```bash
# Clone the repository
git clone https://github.com/codyw912/defuse
cd defuse

# Install development dependencies
uv sync --extra dev

# Run with uv
uv run defuse --help

# Run tests
uv run pytest

# Lint code
uv run ruff check
```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## Support

- Report issues: <https://github.com/codyw912/defuse/issues>
- Dangerzone documentation: <https://dangerzone.rocks>
