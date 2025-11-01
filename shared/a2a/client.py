"""HTTP client helper for interacting with shimmed A2A agent servers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, Dict, Optional, TypeVar
from uuid import uuid4

import httpx

from .models import AgentCard, MessagePayload, MessageResponse

logger = logging.getLogger(__name__)

T = TypeVar("T")


class A2AAgentClient:
    """Minimal async client for talking to an A2A-compatible agent server."""

    def __init__(self, base_url: str, *, timeout: float = 300.0):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self._agent_card: Optional[AgentCard] = None

    async def get_agent_card(self, *, refresh: bool = False) -> AgentCard:
        """Fetch and cache the remote agent card."""

        if self._agent_card is None or refresh:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                response = await client.get(f"{self.base_url}/.well-known/agent.json")
                response.raise_for_status()
                self._agent_card = AgentCard.model_validate(response.json())
                logger.debug("Fetched agent card for %s", self.base_url)
        return self._agent_card

    async def send_message(
        self,
        message: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        streaming: bool = False,
    ) -> MessageResponse:
        """Send a simple text message to the remote agent."""

        payload = MessagePayload(message=message, metadata=metadata, streaming=streaming)

        async with httpx.AsyncClient(timeout=self.timeout) as client:
            response = await client.post(
                f"{self.base_url}/a2a/v1/messages",
                json=payload.model_dump(),
            )
            response.raise_for_status()
            raw_payload = response.json()
            if isinstance(raw_payload, dict):
                if "message_id" not in raw_payload:
                    raw_payload["message_id"] = uuid4().hex
                return MessageResponse.model_validate(raw_payload)

            # Fallback: coerce anything else into a response string
            logger.debug(
                "Unexpected response payload type %s from %s, coercing to text",
                type(raw_payload),
                self.base_url,
            )
            return MessageResponse(
                message_id=uuid4().hex,
                response=str(raw_payload),
            )

    async def invoke_text(
        self,
        message: str,
        *,
        metadata: Optional[Dict[str, Any]] = None,
        streaming: bool = False,
    ) -> str:
        """Convenience helper returning only the response text body."""

        result = await self.send_message(
            message,
            metadata=metadata,
            streaming=streaming,
        )
        return result.response


def run_async_task_sync(awaitable: "asyncio.Future[T] | asyncio.Awaitable[T]") -> T:
    """Run an async task synchronously when no event loop is active."""

    try:
        asyncio.get_running_loop()
    except RuntimeError:
        return asyncio.run(awaitable)

    raise RuntimeError(
        "run_async_task_sync cannot be used when an event loop is already running. "
        "Await the coroutine directly instead.",
    )
