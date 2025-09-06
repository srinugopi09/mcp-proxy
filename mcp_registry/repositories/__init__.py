"""
Data access repositories package.
"""

from .server import ServerRepository
from .capability import CapabilityRepository

__all__ = ["ServerRepository", "CapabilityRepository"]