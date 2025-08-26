# Integration Tests

This directory contains integration tests that verify the complete functionality of Defuse components working together with external dependencies.

## Test Categories

### Container Runtime Integration (`test_container_integration.py`)
Tests actual Docker/Podman container operations:
- Container creation with security constraints
- Resource limit enforcement
- Container cleanup
- Network and filesystem isolation
- Privilege escalation prevention

### CLI Command Integration (`test_cli_integration.py`) 
Tests the command-line interface:
- Download, sanitize, and batch commands
- Configuration persistence
- Error handling and user experience
- Progress indicators and output formatting

### End-to-End Workflows (`test_end_to_end.py`)
Tests complete document processing pipelines:
- Download → Sanitize → Verify workflows
- Multiple document formats (PDF, DOCX, PNG, RTF, etc.)
- Batch processing with mixed success/failure
- Resource management and cleanup
- Performance and efficiency

### Failure Recovery & Security (`test_failure_and_security.py`)
Tests system resilience and security:
- Network timeout recovery
- Disk space exhaustion handling
- Container daemon unavailability
- Malicious input handling (zip bombs, malicious PDFs)
- URL validation and domain restrictions
- Resource exhaustion protection

## Running Integration Tests

### Prerequisites
- Docker or Podman installed and running
- Network connectivity for HTTP mocking tests
- Sufficient disk space for test files

### Run All Integration Tests
```bash
uv run pytest tests/integration/ -v
```

### Run Specific Test Categories
```bash
# Container runtime tests (requires Docker/Podman)
uv run pytest tests/integration/test_container_integration.py -v

# CLI command tests
uv run pytest tests/integration/test_cli_integration.py -v

# End-to-end workflow tests
uv run pytest tests/integration/test_end_to_end.py -v

# Security and failure tests
uv run pytest tests/integration/test_failure_and_security.py -v
```

### Run Tests by Marker
```bash
# All integration tests
uv run pytest -m integration

# Tests requiring Docker specifically  
uv run pytest -m docker

# Slow-running tests
uv run pytest -m slow

# Security-focused tests
uv run pytest -m security

# Network-dependent tests
uv run pytest -m network
```

### Skip Integration Tests
```bash
# Run only unit tests (skip integration)
uv run pytest tests/unit/ -v

# Run all tests except integration
uv run pytest -m "not integration"
```

## Test Environment

Integration tests use controlled environments:
- **Mock HTTP servers** for predictable network responses
- **Temporary directories** for isolated file operations
- **Container runtime mocking** when real containers unavailable
- **Dangerzone CLI mocking** for sanitization testing

## Configuration

Tests use the `integration_config` fixture which provides:
- Conservative resource limits for CI environments
- Verbose output for debugging
- Temporary directories for isolation
- Keep temp files enabled for inspection

## Debugging Integration Test Failures

1. **Check container runtime availability**:
   ```bash
   uv run defuse check-deps
   ```

2. **Run with verbose output**:
   ```bash
   uv run pytest tests/integration/ -v -s
   ```

3. **Run individual test methods**:
   ```bash
   uv run pytest tests/integration/test_container_integration.py::TestDockerIntegration::test_docker_container_creation_and_cleanup -v -s
   ```

4. **Check test artifacts**:
   Integration tests may leave temporary files for inspection when `keep_temp_files=True` is set.

## Performance Considerations

- Integration tests are slower than unit tests due to external dependencies
- Container operations have startup/teardown overhead
- Network mocking adds latency simulation
- Use `-n auto` for parallel execution: `uv run pytest tests/integration/ -n auto`

## Security Testing

The security integration tests verify:
- URL scheme validation (block file://, ftp://, etc.)  
- Domain allowlist enforcement
- File size limit enforcement
- Container isolation boundaries
- Malicious content handling
- Path traversal protection
- Resource exhaustion protection

These tests ensure that Defuse maintains security even under attack conditions.