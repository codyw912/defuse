# Platform-Specific Test Coverage Analysis

**Date**: 2025-10-21  
**Issue**: 38 tests skipped on macOS due to platform constraints  
**Impact**: Untested code paths on Linux and Windows

## Summary of Gaps

### Current Situation
- **Overall coverage**: 90% (on macOS with Docker)
- **Skipped tests**: 38 platform-specific tests
- **Risk**: Platform-specific code paths untested locally

### Breakdown of Skipped Tests

| Category | Count | Risk Level |
|----------|-------|------------|
| **Linux sandbox tools** (Firejail/Bubblewrap) | 16 tests | MEDIUM |
| **Windows-specific** (paths, Docker Desktop) | 13 tests | HIGH |
| **Linux-specific** (resource limits, detection) | 8 tests | MEDIUM |
| **Podman** (not installed locally) | 2 tests | LOW |

## Detailed Gap Analysis

### 1. Linux Sandbox Tools (16 tests skipped)

**Firejail Tests** (7 skipped):
- `test_firejail_noroot_option`
- `test_firejail_seccomp_option`
- `test_firejail_private_tmp`
- `test_firejail_resource_limits`
- `test_firejail_available`
- `test_firejail_command_construction`
- `test_firejail_network_isolation`

**Bubblewrap Tests** (3 skipped):
- `test_bubblewrap_new_session`
- `test_bubblewrap_die_with_parent`
- `test_bubblewrap_unshare_pid`

**Linux Detection/Integration** (6 skipped):
- `test_linux_sandbox_tools_detection`
- `test_bubblewrap_detection`
- `test_linux_sandbox_priority`
- `test_sandbox_backend_selection`
- `test_sandbox_fallback_chain`
- `test_linux_security_report`

**Risk Assessment**: MEDIUM
- Firejail/Bubblewrap marked as "experimental" in docs
- Docker/Podman are primary backends (well-tested)
- GitHub Actions CI tests on actual Linux

### 2. Windows-Specific Tests (13 tests skipped)

**Windows Paths** (3 skipped):
- `test_windows_config_paths`
- `test_windows_path_handling`
- `test_windows_path_errors`

**Windows Docker Desktop** (4 skipped):
- `test_docker_desktop_availability`
- `test_windows_docker_download`
- `test_windows_full_pipeline`
- `test_windows_temp_directory`

**Windows Security** (3 skipped):
- `test_windows_platform_detection`
- `test_windows_sandbox_backends`
- `test_windows_isolation_level`

**Windows Error Handling** (3 skipped):
- `test_windows_permission_errors`
- `test_windows_dangerzone_paths`
- `test_windows_security_report`

**Risk Assessment**: HIGH
- Windows has different path separators, permissions model
- Docker Desktop behaves differently than Linux Docker
- Resource limits API differs (no `resource` module)
- Untested failure modes could cause bad UX

### 3. Podman Tests (2 tests skipped)

**Tests**:
- `test_podman_container_execution`
- `test_macos_podman_integration`

**Risk Assessment**: LOW
- Podman installation is optional
- Podman tests similar command structure to Docker
- Lower priority as Podman is alternative backend

## Options to Improve Coverage

### Option 1: Mock Platform-Specific Behavior ⭐ (Recommended)

**Approach**: Write unit tests that mock `platform.system()` and platform-specific APIs

**Pros**:
- ✅ Can test all platforms from any development machine
- ✅ Fast execution (no VM/container overhead)
- ✅ Tests logic/branching without requiring actual platform
- ✅ Easy to maintain and run in CI

**Cons**:
- ❌ Doesn't catch platform-specific runtime issues
- ❌ Mocks may not match real behavior exactly
- ❌ Tests mock correctness, not real execution

**Implementation Effort**: 4-6 hours
**Coverage Improvement**: +5-7% (would test code paths, not actual execution)

**Example**:
```python
@patch('platform.system')
def test_windows_paths_logic(mock_platform):
    mock_platform.return_value = 'Windows'
    # Test Windows path logic runs correctly
```

### Option 2: Rely on GitHub Actions CI ⭐⭐ (Current Strategy)

**Approach**: Trust CI to test on actual Linux/Windows/macOS runners

**Pros**:
- ✅ Already configured (test.yml has full matrix)
- ✅ Tests on real platforms with real behavior
- ✅ No additional local setup required
- ✅ Catches actual platform-specific bugs

**Cons**:
- ❌ Slower feedback loop (wait for CI)
- ❌ Can't test locally before committing
- ❌ Harder to debug platform-specific failures
- ❌ Requires pushing code to test

**Implementation Effort**: 0 hours (already done)
**Coverage Improvement**: 0% locally, but CI verifies all platforms

**Status**: Already have comprehensive CI matrix

### Option 3: Docker-Based Multi-Platform Testing ⭐⭐

**Approach**: Run Linux tests inside Docker containers on macOS

**Pros**:
- ✅ Can test Linux code paths on macOS
- ✅ Isolated from host system
- ✅ Reproducible environment
- ✅ Firejail/Bubblewrap can be installed in container

**Cons**:
- ❌ Nested containers may not work (Docker in Docker)
- ❌ Firejail/Bubblewrap require privileges that Docker may not allow
- ❌ Still can't test Windows this way
- ❌ Complex setup

**Implementation Effort**: 6-8 hours
**Coverage Improvement**: +3-5% (Linux paths only)

### Option 4: Virtual Machines 

**Approach**: Spin up Ubuntu/Windows VMs for manual testing

**Pros**:
- ✅ Tests on actual platforms
- ✅ Can test interactive behavior
- ✅ Catches real platform bugs

**Cons**:
- ❌ Time-consuming (hours per platform)
- ❌ Manual testing, not automated
- ❌ Requires VM infrastructure
- ❌ Slow feedback loop

**Implementation Effort**: 2-4 hours per platform
**Coverage Improvement**: 0% automated, but validates platforms work

### Option 5: Increase Mock Coverage for Cross-Platform Tests ⭐⭐⭐ (Best Balance)

**Approach**: Combine Options 1 + 2 with some targeted mocking

**Strategy**:
1. **Add platform-agnostic logic tests** (mock platform.system())
2. **Refactor platform-specific code** to be more testable
3. **Keep CI as source of truth** for actual platform execution
4. **Add integration tests** that mock external commands but test logic

**Pros**:
- ✅ Improves local test coverage significantly
- ✅ Tests branching logic without requiring all platforms
- ✅ CI still validates actual execution
- ✅ Faster local development cycle
- ✅ Catches logic errors early

**Cons**:
- ❌ Some duplication between mocked and real tests
- ❌ Mocks must be maintained when implementation changes

**Implementation Effort**: 6-10 hours
**Coverage Improvement**: +5-8% (to ~95-98%)

## Recommendation: Hybrid Approach (Option 5)

**Why**: Best balance of local coverage, CI validation, and maintainability

### Implementation Plan

#### Phase 1: Add Cross-Platform Logic Tests (3-4 hours)

**Target**: Windows-specific code paths

```python
# tests/unit/test_platform_logic.py (new file)

@patch('platform.system')
def test_windows_config_directory_logic(mock_system):
    """Test Windows config path generation without Windows"""
    mock_system.return_value = 'Windows'
    with patch.dict(os.environ, {'APPDATA': 'C:\\Users\\Test\\AppData\\Roaming'}):
        config_dir = get_config_dir()
        assert 'AppData' in str(config_dir)
        assert config_dir.match('**/defuse')

@patch('platform.system')  
def test_linux_config_directory_logic(mock_system):
    """Test Linux config path generation"""
    mock_system.return_value = 'Linux'
    with patch.dict(os.environ, {'HOME': '/home/testuser'}):
        config_dir = get_config_dir()
        assert config_dir == Path('/home/testuser/.config/defuse')

@patch('platform.system')
def test_macos_config_directory_logic(mock_system):
    """Test macOS config path generation"""
    mock_system.return_value = 'Darwin'
    with patch.dict(os.environ, {'HOME': '/Users/testuser'}):
        config_dir = get_config_dir()
        assert 'Library/Application Support' in str(config_dir)
```

**Files to add tests for**:
- Config path generation (Windows/Linux/macOS branches)
- Dangerzone detection logic (different paths per platform)
- Resource limit setting (Windows vs Unix branches)
- Sandbox backend selection (platform-specific availability)

#### Phase 2: Mock Platform Command Construction (2-3 hours)

**Target**: Firejail/Bubblewrap command building

```python
# tests/unit/test_sandbox_commands.py (new file)

def test_firejail_command_construction_logic():
    """Test Firejail command is constructed correctly (mock execution)"""
    config = create_test_config()
    downloader = SandboxedDownloader(config)
    
    # Don't actually run firejail, just verify command structure
    with patch('subprocess.run') as mock_run:
        mock_run.return_value = MagicMock(returncode=0)
        
        # Test command construction logic
        result = downloader.run_firejail_download("http://test.com", Path("/tmp/out"))
        
        # Verify command structure
        call_args = mock_run.call_args[0][0]
        assert call_args[0] == 'firejail'
        assert '--noprofile' in call_args
        assert '--seccomp' in call_args
        assert '--noroot' in call_args
```

#### Phase 3: Refactor for Testability (2-3 hours)

**Extract platform detection**:
```python
# src/defuse/platform_utils.py (new file)

def get_platform():
    """Centralized platform detection (easy to mock)"""
    return platform.system().lower()

def is_windows():
    return get_platform() == 'windows'

def is_linux():
    return get_platform() == 'linux'

def is_macos():
    return get_platform() == 'darwin'
```

Then test all branching through this abstraction.

#### Phase 4: Document Testing Strategy (1 hour)

Update TESTING_STRATEGY.md to clarify:
- Local tests use mocks for platform logic
- CI tests validate actual platform execution
- Platform-specific integration tests run in CI only
- Mock tests catch logic errors, CI catches runtime errors

### Expected Outcomes

**After implementation**:
- ✅ **Local coverage**: ~95-98% (from 90%)
- ✅ **Confidence**: High - logic tested locally, execution tested in CI
- ✅ **Developer experience**: Fast local tests catch most issues
- ✅ **Platform confidence**: CI validates real behavior
- ✅ **Maintainability**: Tests are fast and don't require special setup

**What we DON'T gain**:
- ❌ Won't catch platform-specific runtime bugs until CI
- ❌ Won't catch Docker Desktop quirks until CI runs
- ❌ Mocks could drift from real implementation

**Risk mitigation**:
- CI already tests all platforms comprehensively
- Mock tests catch 80% of issues (logic/branching)
- Integration tests in CI catch remaining 20% (runtime behavior)

## Alternative: Ship with Current Coverage

**Case for shipping now**:
- 90% coverage is excellent
- CI tests all platforms thoroughly  
- Docker/Podman (primary backends) are well-tested locally
- Firejail/Bubblewrap are documented as experimental
- Windows tests will run in CI before release

**Risks of waiting**:
- Diminishing returns (90% → 95% takes significant effort)
- Real bugs come from usage, not test coverage
- Can address platform issues in v0.1.1 based on user feedback

## Decision Matrix

| Approach | Effort | Coverage Gain | Confidence | Recommended? |
|----------|--------|---------------|------------|--------------|
| Mock platform logic | 3-4h | +3-5% | Medium | ✅ Yes |
| Current (CI only) | 0h | 0% | Medium | ⚠️ Acceptable |
| Docker nested testing | 6-8h | +3-5% | Medium | ❌ Too complex |
| VM manual testing | 8-12h | 0% (manual) | High | ⚠️ Time-consuming |
| **Hybrid (recommended)** | **6-10h** | **+5-8%** | **High** | ✅✅ Best |

## Recommendation

**Implement Option 5 (Hybrid)** OR **Ship with current coverage**

### If time allows (6-10 hours available):
- Implement Phase 1-3 of hybrid approach
- Reach 95-98% coverage with platform-agnostic logic tests
- Document testing strategy clearly
- Ship with high confidence

### If time is constrained (ready to ship now):
- Current 90% coverage is strong
- CI validates all platforms
- Ship as v0.1.0 beta with caveat: "Primarily tested on macOS, CI validates Linux/Windows"
- Address platform-specific issues in v0.1.1 based on user feedback

**My recommendation**: Ship now with 90%, add hybrid testing in v0.1.1 if needed. The CI coverage is comprehensive, and real-world usage will reveal actual platform issues faster than synthetic tests.

---

**Next Steps**: Your call - invest 6-10 hours in hybrid testing, or ship with excellent CI coverage?
