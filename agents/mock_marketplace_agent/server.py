from __future__ import annotations

import logging
import os
from typing import Any, Dict, Final, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field

from .agent import MarketplaceProbeAgent

DEFAULT_PORT: Final[int] = 6123
APP_PORT: Final[int] = int(os.getenv("MOCK_AGENT_PORT", DEFAULT_PORT))
APP_HOST: Final[str] = os.getenv("MOCK_AGENT_HOST", "0.0.0.0")
AGENT_ID: Final[str] = "marketplace-probe-001"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger("marketplace_probe_server")


class ExecutePayload(BaseModel):
    """Payload expected by the marketplace /execute contract."""

    request: str = Field(..., description="Task description supplied by the orchestrator")
    context: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional execution context block"
    )
    metadata: Optional[Dict[str, Any]] = Field(
        default=None, description="Optional metadata block (task IDs, user IDs, etc.)"
    )


app = FastAPI(
    title="Marketplace Probe Agent",
    description=(
        "Helper service to validate the agent registration + execution flow. "
        "It simply echoes the payload so you can confirm the orchestrator reached your endpoint."
    ),
    version="0.1.0",
)

agent = MarketplaceProbeAgent()


@app.get("/.well-known/agent.json", tags=["metadata"])
async def agent_card() -> Dict[str, Any]:
    """Expose metadata similar to ERC-8004 for manual inspection."""

    return {
        "id": AGENT_ID,
        "name": "Marketplace Probe Agent",
        "description": "Loopback agent that helps verify the marketplace submission flow.",
        "version": "0.1.0",
        "capabilities": [
            {"name": "echo", "description": "Echoes the request/context/metadata payloads."},
            {"name": "diagnostics", "description": "Adds timestamps and call counters to responses."},
        ],
        "endpoints": {
            "execute": f"http://127.0.0.1:{APP_PORT}/execute",
            "health": f"http://127.0.0.1:{APP_PORT}/health",
        },
        "extras": {
            "streaming": False,
            "expected_payload": ["request", "context", "metadata"],
        },
    }


@app.get("/health", tags=["diagnostics"])
async def health() -> Dict[str, Any]:
    """Quick readiness endpoint used by curl or automated probes."""

    return {
        "status": "ok",
        "agent_id": AGENT_ID,
        "calls_handled": agent.invocation_count,
        "default_execute_url": f"http://127.0.0.1:{APP_PORT}/execute",
    }


@app.post("/execute", tags=["execution"])
async def execute(payload: ExecutePayload) -> Dict[str, Any]:
    """Primary entry point invoked by the marketplace orchestrator."""

    logger.info("POST /execute received (request length=%s)", len(payload.request))
    return await agent.run(
        payload.request,
        context=payload.context,
        metadata=payload.metadata,
    )


def main() -> None:
    """CLI entry point."""

    import uvicorn

    uvicorn.run(app, host=APP_HOST, port=APP_PORT, log_level="info")


if __name__ == "__main__":
    main()
