"""Mock marketplace agent service for manual end-to-end testing."""

from .server import APP_PORT, app  # noqa: F401

__all__ = ["app", "APP_PORT"]
