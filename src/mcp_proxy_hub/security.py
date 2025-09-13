"""Security validation utilities for MCP Proxy Hub."""

import ipaddress
from urllib.parse import urlparse

from fastapi import HTTPException

from .config import settings


def _is_private_ip(hostname: str) -> bool:
    """Return True if the hostname/IP points to a private or local network.

    This function attempts to parse the host as an IP address. If the
    conversion fails it assumes the host is a domain and allows it (DNS
    resolution is not performed here). Localhost and loopback addresses
    are explicitly denied via `DENIED_HOSTS`.
    
    Args:
        hostname: The hostname or IP address to check
        
    Returns:
        True if the hostname is a private/local IP, False otherwise
    """
    try:
        ip = ipaddress.ip_address(hostname)
        return ip.is_private or ip.is_loopback or ip.is_link_local
    except ValueError:
        return False


def validate_remote_url(url: str) -> None:
    """Validate that the remote URL uses an allowed scheme and host.

    This function enforces security policies to prevent SSRF attacks
    and other misuse by validating the URL scheme and hostname.
    
    Args:
        url: The URL to validate
        
    Raises:
        HTTPException: If the URL is not allowed (400 status code)
    """
    parsed = urlparse(url)
    
    # Check scheme
    if parsed.scheme not in settings.allowed_schemes:
        raise HTTPException(
            status_code=400, 
            detail=f"Only {'/'.join(settings.allowed_schemes).upper()} MCP servers are supported"
        )
    
    # Check hostname
    host = parsed.hostname or ""
    if host in settings.denied_hosts or _is_private_ip(host):
        raise HTTPException(
            status_code=400, 
            detail="Connection to local/private hosts is denied"
        )