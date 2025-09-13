"""Unit tests for security module."""

import pytest
from fastapi import HTTPException

from mcp_proxy_hub.security import _is_private_ip, validate_remote_url


class TestIsPrivateIp:
    """Test the _is_private_ip function."""

    def test_private_ipv4_addresses(self):
        """Test that private IPv4 addresses are detected."""
        assert _is_private_ip("192.168.1.1") is True
        assert _is_private_ip("10.0.0.1") is True
        assert _is_private_ip("172.16.0.1") is True

    def test_public_ipv4_addresses(self):
        """Test that public IPv4 addresses are not detected as private."""
        assert _is_private_ip("8.8.8.8") is False
        assert _is_private_ip("1.1.1.1") is False
        assert _is_private_ip("208.67.222.222") is False

    def test_loopback_addresses(self):
        """Test that loopback addresses are detected."""
        assert _is_private_ip("127.0.0.1") is True
        assert _is_private_ip("::1") is True

    def test_link_local_addresses(self):
        """Test that link-local addresses are detected."""
        assert _is_private_ip("169.254.1.1") is True
        assert _is_private_ip("fe80::1") is True

    def test_domain_names(self):
        """Test that domain names are not detected as private IPs."""
        assert _is_private_ip("example.com") is False
        assert _is_private_ip("google.com") is False
        assert _is_private_ip("localhost") is False  # Domain, not IP

    def test_invalid_ip_addresses(self):
        """Test that invalid IP addresses are handled gracefully."""
        assert _is_private_ip("not.an.ip") is False
        assert _is_private_ip("999.999.999.999") is False
        assert _is_private_ip("") is False


class TestValidateRemoteUrl:
    """Test the validate_remote_url function."""

    def test_valid_http_url(self):
        """Test that valid HTTP URLs pass validation."""
        # Should not raise an exception
        validate_remote_url("http://example.com/mcp")

    def test_valid_https_url(self):
        """Test that valid HTTPS URLs pass validation."""
        # Should not raise an exception
        validate_remote_url("https://example.com/mcp")

    def test_invalid_scheme(self):
        """Test that invalid schemes are rejected."""
        with pytest.raises(HTTPException) as exc_info:
            validate_remote_url("ftp://example.com/mcp")
        
        assert exc_info.value.status_code == 400
        assert "HTTP/HTTPS" in exc_info.value.detail

    def test_denied_localhost(self):
        """Test that localhost is denied."""
        with pytest.raises(HTTPException) as exc_info:
            validate_remote_url("http://localhost/mcp")
        
        assert exc_info.value.status_code == 400
        assert "local/private hosts" in exc_info.value.detail

    def test_denied_loopback_ip(self):
        """Test that loopback IPs are denied."""
        with pytest.raises(HTTPException) as exc_info:
            validate_remote_url("http://127.0.0.1/mcp")
        
        assert exc_info.value.status_code == 400
        assert "local/private hosts" in exc_info.value.detail

    def test_denied_private_ip(self):
        """Test that private IPs are denied."""
        with pytest.raises(HTTPException) as exc_info:
            validate_remote_url("http://192.168.1.1/mcp")
        
        assert exc_info.value.status_code == 400
        assert "local/private hosts" in exc_info.value.detail

    def test_allowed_public_ip(self):
        """Test that public IPs are allowed."""
        # Should not raise an exception
        validate_remote_url("http://8.8.8.8/mcp")

    def test_allowed_domain(self):
        """Test that domains are allowed."""
        # Should not raise an exception
        validate_remote_url("https://api.example.com/mcp")

    def test_url_with_port(self):
        """Test URLs with custom ports."""
        # Should not raise an exception
        validate_remote_url("https://example.com:8080/mcp")

    def test_url_with_path(self):
        """Test URLs with paths."""
        # Should not raise an exception
        validate_remote_url("https://example.com/api/v1/mcp")

    def test_url_with_query_params(self):
        """Test URLs with query parameters."""
        # Should not raise an exception
        validate_remote_url("https://example.com/mcp?version=1")