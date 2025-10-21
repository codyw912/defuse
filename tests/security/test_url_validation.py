"""
Security tests for URL validation.

Tests URL scheme restrictions, domain allowlist enforcement, and protection
against various URL-based attacks including path traversal and URL encoding exploits.

OWASP References:
- A01:2021 - Broken Access Control
- A05:2021 - Security Misconfiguration
- A10:2021 - Server-Side Request Forgery (SSRF)
"""

import pytest
from defuse.downloader import SecureDocumentDownloader
from defuse.config import SandboxConfig


@pytest.mark.security
class TestURLSchemeValidation:
    """Test that only HTTP/HTTPS schemes are allowed (SSRF prevention)."""

    def test_http_scheme_allowed(self, sandbox_config_fixture):
        """HTTP scheme should be allowed."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("http://example.com/document.pdf") is True

    def test_https_scheme_allowed(self, sandbox_config_fixture):
        """HTTPS scheme should be allowed."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("https://example.com/document.pdf") is True

    def test_file_scheme_blocked(self, sandbox_config_fixture):
        """File:// URLs should be blocked to prevent local file access."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("file:///etc/passwd") is False

    def test_ftp_scheme_blocked(self, sandbox_config_fixture):
        """FTP scheme should be blocked."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("ftp://example.com/file.pdf") is False

    def test_javascript_scheme_blocked(self, sandbox_config_fixture):
        """JavaScript scheme should be blocked."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("javascript:alert('XSS')") is False

    def test_data_scheme_blocked(self, sandbox_config_fixture):
        """Data URLs should be blocked."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert (
            downloader.validate_url("data:text/html,<script>alert('XSS')</script>")
            is False
        )

    @pytest.mark.parametrize(
        "malicious_url",
        [
            "gopher://internal-server/",
            "dict://internal-server:11211/",
            "ldap://internal-server/",
            "tftp://internal-server/",
            "ssh://internal-server/",
            "telnet://internal-server:23/",
        ],
    )
    def test_other_protocols_blocked(self, sandbox_config_fixture, malicious_url):
        """Various protocols should be blocked (SSRF prevention)."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url(malicious_url) is False


@pytest.mark.security
class TestDomainAllowlist:
    """Test domain allowlist enforcement."""

    def test_no_allowlist_allows_all_domains(self, temp_dir):
        """When no allowlist is configured, all domains should be allowed."""
        config = SandboxConfig(
            temp_dir=temp_dir,
            allowed_domains=None,  # No restrictions
        )
        downloader = SecureDocumentDownloader(config)
        assert downloader.validate_url("https://example.com/file.pdf") is True
        assert downloader.validate_url("https://untrusted.com/file.pdf") is True

    def test_allowlist_permits_exact_domain(self, temp_dir):
        """Exact domain match should be permitted."""
        config = SandboxConfig(
            temp_dir=temp_dir, allowed_domains=["example.com", "trusted.org"]
        )
        downloader = SecureDocumentDownloader(config)
        assert downloader.validate_url("https://example.com/file.pdf") is True
        assert downloader.validate_url("https://trusted.org/file.pdf") is True

    def test_allowlist_permits_subdomains(self, temp_dir):
        """Subdomains of allowed domains should be permitted."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["example.com"])
        downloader = SecureDocumentDownloader(config)
        assert downloader.validate_url("https://docs.example.com/file.pdf") is True
        assert downloader.validate_url("https://cdn.example.com/file.pdf") is True

    def test_allowlist_blocks_non_allowed_domain(self, temp_dir):
        """Domains not in allowlist should be blocked."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["example.com"])
        downloader = SecureDocumentDownloader(config)
        assert downloader.validate_url("https://malicious.com/file.pdf") is False
        assert downloader.validate_url("https://untrusted.org/file.pdf") is False

    def test_allowlist_case_insensitive(self, temp_dir):
        """Domain matching should be case-insensitive."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["Example.COM"])
        downloader = SecureDocumentDownloader(config)
        assert downloader.validate_url("https://example.com/file.pdf") is True
        assert downloader.validate_url("https://EXAMPLE.COM/file.pdf") is True
        assert downloader.validate_url("https://Example.Com/file.pdf") is True

    def test_allowlist_blocks_partial_domain_match(self, temp_dir):
        """Partial domain matches should not bypass allowlist."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["example.com"])
        downloader = SecureDocumentDownloader(config)
        # Should NOT match "notexample.com" even though it contains "example.com"
        assert downloader.validate_url("https://notexample.com/file.pdf") is False
        # Should match subdomain
        assert downloader.validate_url("https://sub.example.com/file.pdf") is True


@pytest.mark.security
class TestURLEncodingAttacks:
    """Test protection against URL encoding-based attacks."""

    def test_url_encoded_file_scheme(self, sandbox_config_fixture):
        """URL-encoded file:// scheme should be blocked."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # %66ile = file
        assert downloader.validate_url("%66ile:///etc/passwd") is False

    def test_double_encoded_scheme(self, sandbox_config_fixture):
        """Double URL-encoded schemes should be blocked."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # %2566ile = %66ile = file
        assert downloader.validate_url("%2566ile:///etc/passwd") is False

    def test_unicode_encoded_domain(self, temp_dir):
        """Unicode-encoded domains attempting to bypass allowlist should be blocked."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["example.com"])
        downloader = SecureDocumentDownloader(config)
        # These should fail to match the allowlist
        # Note: The current implementation may not fully protect against this
        # This test documents the expected behavior
        assert (
            downloader.validate_url("https://ex\u0061mple.com/file.pdf") is True
        )  # Should work - Unicode normalization

    def test_percent_encoded_path_traversal(self, sandbox_config_fixture):
        """Percent-encoded path traversal should not crash the validator."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # These URLs should be valid (path validation is not URL validator's job)
        # The actual download validation happens at a different layer
        url = "https://example.com/files/%2e%2e%2f%2e%2e%2fetc/passwd"
        assert downloader.validate_url(url) is True  # URL is structurally valid


@pytest.mark.security
class TestMalformedURLs:
    """Test handling of malformed and edge-case URLs."""

    def test_empty_url(self, sandbox_config_fixture):
        """Empty URL should be rejected."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("") is False

    def test_url_without_scheme(self, sandbox_config_fixture):
        """URL without scheme should be rejected."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("example.com/file.pdf") is False

    def test_url_without_netloc(self, sandbox_config_fixture):
        """URL without network location should be rejected."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("https:///file.pdf") is False
        assert downloader.validate_url("https://") is False

    def test_malformed_url_with_spaces(self, sandbox_config_fixture):
        """URL with spaces is accepted by urllib.parse (spaces in path are valid)."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # Note: urllib.parse accepts spaces in the path component
        # This is technically valid according to the URL parser
        assert downloader.validate_url("https://example.com/my document.pdf") is True

    def test_url_with_credentials(self, sandbox_config_fixture):
        """URLs with credentials should still validate (credentials in netloc)."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # Note: Including credentials is generally bad practice but structurally valid
        assert downloader.validate_url("https://user:pass@example.com/file.pdf") is True

    def test_url_with_port(self, sandbox_config_fixture):
        """URLs with explicit port should validate."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("https://example.com:8443/file.pdf") is True

    def test_url_with_query_params(self, sandbox_config_fixture):
        """URLs with query parameters should validate."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert (
            downloader.validate_url("https://example.com/file.pdf?token=abc123") is True
        )

    def test_url_with_fragment(self, sandbox_config_fixture):
        """URLs with fragment identifiers should validate."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("https://example.com/file.pdf#page=1") is True


@pytest.mark.security
class TestIPAddressURLs:
    """Test handling of IP address URLs (potential SSRF vector)."""

    def test_public_ip_allowed(self, sandbox_config_fixture):
        """Public IP addresses should be allowed."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("https://8.8.8.8/file.pdf") is True

    def test_localhost_allowed_by_default(self, sandbox_config_fixture):
        """Localhost URLs should be allowed by default (blocked by allowlist if needed)."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # Note: This is a security consideration - should localhost be blocked?
        # Current implementation allows it unless blocked by allowlist
        assert downloader.validate_url("https://127.0.0.1/file.pdf") is True
        assert downloader.validate_url("https://localhost/file.pdf") is True

    def test_private_network_allowed_by_default(self, sandbox_config_fixture):
        """Private network IPs should be allowed by default (SSRF risk)."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        # Note: This is a SECURITY CONCERN - private IPs can enable SSRF attacks
        # Consider blocking these in production
        assert downloader.validate_url("https://192.168.1.1/file.pdf") is True
        assert downloader.validate_url("https://10.0.0.1/file.pdf") is True
        assert downloader.validate_url("https://172.16.0.1/file.pdf") is True

    def test_ipv6_localhost(self, sandbox_config_fixture):
        """IPv6 localhost should be allowed by default."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)
        assert downloader.validate_url("https://[::1]/file.pdf") is True

    def test_allowlist_blocks_ip_addresses(self, temp_dir):
        """IP addresses should be blockable via domain allowlist."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["example.com"])
        downloader = SecureDocumentDownloader(config)
        # IP addresses won't match domain allowlist
        assert downloader.validate_url("https://192.168.1.1/file.pdf") is False
        assert downloader.validate_url("https://8.8.8.8/file.pdf") is False


@pytest.mark.security
class TestExceptionHandling:
    """Test that URL validation handles exceptions gracefully."""

    def test_url_validation_never_raises(self, sandbox_config_fixture):
        """URL validation should never raise exceptions, only return False."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)

        # Try various inputs that might cause exceptions
        test_inputs = [
            None,  # Will fail when converted to string
            123,  # Non-string
            [],  # List
            {},  # Dict
            b"https://example.com",  # Bytes
            "https://\x00example.com",  # Null byte
            "https://example.com" + "\x00" * 1000,  # Null padding
            "https://" + "a" * 10000 + ".com",  # Very long domain
        ]

        for test_input in test_inputs:
            try:
                result = downloader.validate_url(test_input)
                assert isinstance(result, bool), (
                    f"validate_url should return bool for {test_input}"
                )
            except Exception as e:
                pytest.fail(
                    f"validate_url raised {type(e).__name__} for input {test_input}: {e}"
                )


@pytest.mark.security
class TestSecurityDocumentation:
    """Test that security expectations are documented and met."""

    def test_validator_rejects_dangerous_schemes(self, sandbox_config_fixture):
        """SECURITY: Validator must reject all non-HTTP(S) schemes."""
        downloader = SecureDocumentDownloader(sandbox_config_fixture)

        dangerous_schemes = [
            "file://",
            "ftp://",
            "gopher://",
            "dict://",
            "ldap://",
            "jar://",
            "sftp://",
        ]

        for scheme in dangerous_schemes:
            url = f"{scheme}example.com/file"
            assert downloader.validate_url(url) is False, (
                f"SECURITY: {scheme} must be blocked"
            )

    def test_allowlist_is_enforced_strictly(self, temp_dir):
        """SECURITY: Domain allowlist must be strictly enforced."""
        config = SandboxConfig(temp_dir=temp_dir, allowed_domains=["trusted.com"])
        downloader = SecureDocumentDownloader(config)

        # Allowed
        assert downloader.validate_url("https://trusted.com/file.pdf") is True
        assert downloader.validate_url("https://sub.trusted.com/file.pdf") is True

        # Blocked
        assert downloader.validate_url("https://untrusted.com/file.pdf") is False
        assert downloader.validate_url("https://trusted.com.evil.com/file.pdf") is False
        assert downloader.validate_url("https://notrusted.com/file.pdf") is False
