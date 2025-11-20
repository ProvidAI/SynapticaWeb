from __future__ import annotations

import asyncio
import logging
from datetime import datetime, timezone
from typing import Any, Dict, Optional


class MarketplaceProbeAgent:
    """Simple echo-style agent that records each invocation for debugging."""

    def __init__(self, *, artificial_delay: float = 0.25) -> None:
        self.artificial_delay = artificial_delay
        self.invocation_count = 0
        self.logger = logging.getLogger(self.__class__.__name__)

    async def run(
        self,
        request_text: str,
        *,
        context: Optional[Dict[str, Any]] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """Handle incoming orchestrator prompts with a diagnostic response."""

        self.invocation_count += 1
        context = context or {}
        metadata = metadata or {}

        self.logger.info(
            "marketplace-probe request #%s | request=%s | context=%s | metadata=%s",
            self.invocation_count,
            request_text,
            context,
            metadata,
        )

        if self.artificial_delay > 0:
            await asyncio.sleep(self.artificial_delay)

        timestamp = datetime.now(timezone.utc).isoformat()

        return {
            "success": True,
            "agent_id": "marketplace-probe-001",
            "result": {
                "summary": "Marketplace probe agent echoed your input.",
                "timestamp": timestamp,
                "call_number": self.invocation_count,
                "original_request": request_text,
                "context_received": context,
            },
            "metadata": {
                "probe": True,
                "echoed_metadata": metadata,
                "delay_seconds": self.artificial_delay,
                "handled_at": timestamp,
            },
        }
