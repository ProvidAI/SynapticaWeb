"""Shared Pydantic models for the lightweight A2A shim."""

from __future__ import annotations

from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class AgentCapability(BaseModel):
    """Describes a high-level capability the agent exposes."""

    name: str
    description: Optional[str] = None


class AgentCard(BaseModel):
    """Metadata describing an exposed agent."""

    id: str
    name: str
    description: str
    version: str = "0.1.0"
    capabilities: List[AgentCapability] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    extras: Dict[str, Any] = Field(default_factory=dict)


class MessagePayload(BaseModel):
    """Inbound message payload for the shimmed A2A transport."""

    message: str
    metadata: Optional[Dict[str, Any]] = None
    streaming: bool = False


class MessageResponse(BaseModel):
    """Outbound response payload from the shimmed A2A transport."""

    message_id: str
    response: str
    metadata: Optional[Dict[str, Any]] = None
