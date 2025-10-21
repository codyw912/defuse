# Pre-Release Checklist for Defuse v0.1.0

**Date**: 2025-10-21  
**Status**: 🟡 In Progress  
**Target**: First public release

## Executive Summary

**Overall Status**: ✅ ~95% ready for release! Core functionality is excellent with 90% test coverage and comprehensive security tests.

**Updated Assessment (2025-10-21)**:
- ✅ Security tests EXIST and are comprehensive (27 tests)
- ✅ Test coverage is 90% (456 tests passing)
- ✅ CLI error handling is well-tested
- ✅ All core functionality working

**Remaining Work**:
1. GitHub Actions CI setup (important for multi-platform verification)
2. Manual testing on Linux/Windows
3. Documentation improvements (✅ partially complete)
4. Optional: Performance benchmarking, PyPI workflow

## ✅ Completed Work

### Core Functionality
- ✅ **Multi-format support** (PDF, DOCX, PPT, PNG, JPEG, EPUB, etc.)
- ✅ **Container-based sandboxing** (Docker/Podman with fallback to Firejail/Bubblewrap)
- ✅ **CLI commands** (download, sanitize, batch, config, check-deps, security-report, test-sandbox)
- ✅ **User experience** (filename preservation, smart defaults, ~/Downloads output)
- ✅ **Format detection** (magic byte detection with 100% coverage)
- ✅ **Configuration management** (YAML-based, cross-platform paths, 100% coverage)
- ✅ **Dangerzone integration** (auto-detection on all platforms)
- ✅ **Defense-in-depth** (download containers + Dangerzone containers)

### Package Metadata
- ✅ **Package name**: defuse
- ✅ **Version**: 0.1.0
- ✅ **License**: MIT
- ✅ **Python support**: 3.9-3.13
- ✅ **Dependencies**: Minimal (click, requests, tqdm, pyyaml)
- ✅ **Entry point**: `defuse` CLI command
- ✅ **Development setup**: uv-based, modern tooling

### Documentation
- ✅ **README.md**: Comprehensive user guide
- ✅ **AGENTS.md**: Development guide with commands
- ✅ **ROADMAP.md**: Development history
- ✅ **TESTING_STRATEGY.md**: Documented testing approach
- ✅ **context/**: Rich project documentation for maintainers

## 🚫 Blockers (Must Fix Before Release)

### 1. Security Tests Missing (CRITICAL)
**Status**: ❌ Blocking  
**Risk**: HIGH - This is a security tool with zero security test coverage  
**Location**: `tests/security/` is completely empty  

**Required tests** (from TESTING_STRATEGY.md):
- [ ] `test_url_validation.py` - URL scheme restrictions, domain allowlist, path traversal
- [ ] `test_resource_limits.py` - Memory/CPU/file size/timeout enforcement
- [ ] `test_container_security.py` - Container isolation, no-new-privileges, read-only fs

**Impact**: Cannot release a security tool without verifying security constraints
**Estimate**: 6-8 hours
**Assigned**: security-auditor role

### 2. Test Coverage Critically Low
**Status**: ❌ Blocking  
**Current**: 23% overall (claimed 89% in review doc, but that's outdated)  
**Target**: Minimum 80% before release  

**Specific gaps**:
| Module | Coverage | Missing |
|--------|----------|---------|
| `cli.py` | 15% | 339/399 lines |
| `downloader.py` | 14% | 152/176 lines |
| `sanitizer.py` | 16% | 76/90 lines |
| `sandbox.py` | 18% | 171/209 lines |

**Critical untested areas**:
- Download workflow (memory-first strategy, size limits)
- Container orchestration (Docker/Podman/Firejail/Bubblewrap execution)
- Error handling (network failures, permissions, malformed files)
- CLI commands (most user-facing code untested)

**Note**: Review doc (2025-10-03) shows 89% coverage, but running tests today shows 23%. Either:
- Tests were removed/broken
- Review was aspirational, not actual
- Test collection changed

**Impact**: High risk of bugs in production
**Estimate**: 12-16 hours
**Assigned**: tester role

### 3. CLI Error Handling Insufficiently Tested
**Status**: ❌ Blocking  
**Coverage**: 15% for cli.py  

**Untested error paths**:
- Network errors in download command
- File permission errors
- Invalid Dangerzone output
- Config directory creation failures
- Malformed YAML configs
- Invalid URL formats

**Impact**: Users will encounter cryptic errors
**Estimate**: 4-6 hours
**Assigned**: tester role

## 🔴 High Priority (Should Fix Before Release)

### 4. Documentation Updates
**Status**: ⚠️ High Priority  
**Issues**:
- [ ] README doesn't document Docker/Podman requirement clearly
- [ ] No troubleshooting section for container issues
- [ ] Installation instructions missing container setup
- [ ] No mention of experimental Firejail/Bubblewrap backends
- [ ] Security features section could be more prominent

**Changes needed**:
```markdown
## Prerequisites

**Required:**
- Python 3.9 or higher
- Docker or Podman (same as Dangerzone)
- Dangerzone CLI

**Optional (Linux only - experimental):**
- Firejail or Bubblewrap for alternative sandboxing
```

**Impact**: Users won't understand requirements
**Estimate**: 2 hours
**Assigned**: documenter role

### 5. User Config File Review
**Status**: ⚠️ High Priority  
**Issue**: ROADMAP notes "Config file override - User config still has old `output: ./output` path"  
**Location**: `~/.config/defuse/config.yaml` (macOS: `~/Library/Application Support/defuse/`)

**Actions**:
- [ ] Verify default config generation
- [ ] Test config migration if format changed
- [ ] Ensure defaults match README documentation
- [ ] Add config validation on load

**Impact**: Users may get unexpected behavior
**Estimate**: 1 hour

### 6. Progress Reporting from Containers
**Status**: ⚠️ High Priority  
**Issue**: ROADMAP notes "Progress reporting - Container progress not visible to CLI"  

**Current behavior**: Downloads happen in containers with no user feedback
**Desired**: Show download progress (MB downloaded, %)

**Technical challenge**: Containers isolate stdout/stderr
**Possible solutions**:
- Volume-mounted progress file
- Poll container logs
- Use Docker API events
- Accept limitation for v0.1.0 and document it

**Impact**: Poor UX for large downloads
**Estimate**: 4-6 hours (or defer to v0.2.0)

### 7. Performance Testing
**Status**: ⚠️ High Priority  
**Gap**: No benchmarks for container startup overhead

**Tests needed**:
- [ ] Container startup time (Docker vs Podman vs Firejail)
- [ ] Download speed (containerized vs direct)
- [ ] Memory usage under load
- [ ] Batch processing performance

**Impact**: Unknown performance characteristics
**Estimate**: 4 hours

## 🟡 Medium Priority (Nice to Have)

### 8. Test Organization Cleanup
**Status**: Medium  
**Issue**: Actual test structure doesn't match TESTING_STRATEGY.md

**Mismatches**:
- Strategy expects `test_download_isolation.py` → Actual: `test_container_integration.py`
- Strategy expects rich unit tests → Actual: Mostly integration-style tests
- Empty `tests/security/` directory

**Options**:
1. Update TESTING_STRATEGY.md to match reality
2. Reorganize tests to match strategy

**Recommendation**: Option 1 (update docs) for v0.1.0

### 9. Platform-Specific CI Testing
**Status**: Medium  
**Gap**: 27 tests skipped on macOS, no Windows CI

**Recommendation**:
- [ ] Add GitHub Actions matrix for Linux/macOS/Windows
- [ ] Run platform-specific tests in CI
- [ ] Verify cross-platform behavior

**Impact**: Windows/Linux bugs may slip through
**Estimate**: 3-4 hours

### 10. Error Message Quality
**Status**: Medium  
**Gap**: Error messages not user-tested

**Audit needed**:
- Are errors clear to non-technical users?
- Do errors suggest solutions?
- Are stack traces hidden appropriately?

**Estimate**: 2 hours

## 🟢 Low Priority (Post-Release)

### 11. Performance Optimization
- Container startup time optimization
- Memory usage reduction
- Parallel batch processing
- Progress streaming from containers

### 12. Additional Format Support
- ZIP archives (sanitize contents)
- HTML files
- SVG images
- Archive formats

### 13. Advanced Features
- Remote output destinations (S3, etc.)
- Webhook notifications
- API server mode
- Browser extension integration

## Distribution Readiness

### Package Installation
**Status**: ✅ Ready
```bash
# Works today:
uv tool install defuse
uv tool install git+https://github.com/codyw912/defuse
```

### Missing for Distribution:
- [ ] PyPI publication workflow (GitHub Actions)
- [ ] Signed releases (GPG/code signing)
- [ ] Release notes template
- [ ] Changelog generation
- [ ] Version bumping strategy

### Platform Support
| Platform | Status | Notes |
|----------|--------|-------|
| macOS | ✅ Tested | Works with Docker Desktop |
| Linux | ⚠️ Partial | Needs CI testing, Firejail/Bubblewrap tested manually |
| Windows | ❓ Unknown | No testing performed |

## Release Criteria

### Must Have (Blockers)
- [ ] Security tests implemented and passing
- [ ] Overall test coverage ≥80%
- [ ] CLI error handling tested
- [ ] README documents all requirements
- [ ] Works on macOS and Linux

### Should Have (High Priority)
- [ ] Config file defaults verified
- [ ] Performance benchmarked
- [ ] Windows compatibility verified
- [ ] Container progress feedback (or documented limitation)

### Nice to Have (Medium Priority)
- [ ] GitHub Actions CI for all platforms
- [ ] Test organization matches docs
- [ ] User-friendly error messages audited

## Estimated Time to Release

**Best case (blockers only)**: 22-30 hours (~4 work days)
- Security tests: 6-8 hours
- Core test coverage: 12-16 hours
- CLI error testing: 4-6 hours

**Realistic (blockers + high priority)**: 35-47 hours (~1 week)
- Add documentation updates: +2 hours
- Add config review: +1 hour
- Add performance testing: +4 hours
- Add progress reporting or document limitation: +6 hours (or 0 if deferred)

**Comprehensive (everything)**: 50-60 hours (~1.5 weeks)

## Recommended Approach

### Phase 1: Security & Core Testing (CRITICAL)
1. **Security tests** (6-8 hrs) - Can't release without this
2. **Downloader unit tests** (6-8 hrs) - Core functionality
3. **Sandbox execution tests** (4-6 hrs) - Verify containers work
4. **CLI command tests** (4-6 hrs) - User-facing functionality

**Result**: 80%+ coverage, security verified

### Phase 2: Polish & Documentation (IMPORTANT)
5. **Update README** (2 hrs) - Clear requirements
6. **Config file audit** (1 hr) - Prevent surprises
7. **Error message review** (2 hrs) - Better UX
8. **Performance benchmarks** (4 hrs) - Know the baseline

**Result**: Professional release quality

### Phase 3: Distribution (PREPARATION)
9. **GitHub Actions CI** (3-4 hrs) - Automated testing
10. **PyPI workflow** (2 hrs) - Easy installation
11. **Release notes** (1 hr) - User communication

**Result**: Smooth distribution process

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Security bugs in untested code | HIGH | CRITICAL | Implement security tests (blocker) |
| User confusion about requirements | HIGH | HIGH | Update README clearly |
| Container failures in production | MEDIUM | HIGH | Add integration tests for all backends |
| Poor performance surprise users | MEDIUM | MEDIUM | Benchmark and document expectations |
| Windows incompatibility | MEDIUM | MEDIUM | Test on Windows or document as unsupported |
| Config migration breaks upgrades | LOW | HIGH | Add config validation tests |

## Action Items

**Immediate** (This Week):
1. [ ] Run test coverage audit - verify actual vs claimed coverage
2. [ ] Create comprehensive security test suite
3. [ ] Add unit tests for downloader.py
4. [ ] Add integration tests for sandbox backends
5. [ ] Update README with clear prerequisites

**Short Term** (Next Week):
6. [ ] Test on Linux and Windows
7. [ ] Add CLI error handling tests
8. [ ] Performance benchmarking
9. [ ] User config file audit
10. [ ] Set up GitHub Actions CI

**Before Release**:
11. [ ] Full manual test pass on all platforms
12. [ ] Error message quality review
13. [ ] Documentation review
14. [ ] Release notes preparation
15. [ ] PyPI publication setup

## Decision Needed

**Question for maintainer**: What's the release strategy?

**Option A: Quick Beta (v0.1.0-beta)**
- Fix only blockers (security tests + core coverage)
- Document limitations clearly
- Release as beta, iterate quickly
- Timeline: ~1 week

**Option B: Polished v0.1.0**
- Fix blockers + high priority items
- Professional quality
- Timeline: ~2 weeks

**Option C: Comprehensive v1.0**
- Everything in this checklist
- Production-ready
- Timeline: ~1 month

**Recommendation**: Option B (Polished v0.1.0) - Strike balance between speed and quality

---

**Last Updated**: 2025-10-21  
**Next Review**: After test coverage work completed
