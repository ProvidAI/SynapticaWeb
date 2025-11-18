"""Registry helpers for on-chain agent management."""

from .registrar import (
    AgentRegistryClient,
    AgentRegistryConfigError,
    AgentRegistryRegistrationError,
    AgentRegistryResult,
    get_registry_client,
)

__all__ = [
    "AgentRegistryClient",
    "AgentRegistryConfigError",
    "AgentRegistryRegistrationError",
    "AgentRegistryResult",
    "get_registry_client",
]
