"""Temporary A2A transport shim.

This module centralises how we emit Agent-to-Agent (A2A) messages while
the dedicated transport/broker integration is still under construction.
By funnelling all message emission through the helpers below we make it
easy to plug in the real delivery mechanism later without touching the
business logic in negotiator/verifier tools.

The helpers intentionally no-op beyond structured logging so existing
agents can continue to operate synchronously. Once the transport is
available, replace the body of :func:`publish_message` (and optionally
add queue/backpressure handling) without needing to refactor callers.
"""

from __future__ import annotations

import logging
from typing import Iterable

from .a2a import A2AMessage

logger = logging.getLogger(__name__)


def publish_message(message: A2AMessage, *, tags: Iterable[str] | None = None) -> None:
    """Publish an A2A message via the temporary shim.

    Args:
        message: Fully constructed A2A envelope to emit.
        tags: Optional iterable of hint strings that transport/broker
            implementations can use for routing or filtering.

    The current implementation simply logs the message payload. This
    keeps the call sites in place so we can introduce the actual
    transport later without altering agent behaviour.
    """

    tag_suffix = f" tags={list(tags)}" if tags else ""
    logger.info(
        "A2A publish %s->%s type=%s%s body=%s",
        message.from_agent,
        message.to_agent,
        message.type,
        tag_suffix,
        message.body,
    )


__all__ = ["publish_message"]
