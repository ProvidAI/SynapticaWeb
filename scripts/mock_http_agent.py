#!/usr/bin/env python
"""
Minimal HTTP agent for manual marketplace testing.

Run with:
    uv run python scripts/mock_http_agent.py

Endpoints:
    GET  /health   -> {"status": "ok"}
    POST /execute  -> echoes request payload with mock result
"""

from __future__ import annotations

import os
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import FastAPI
from pydantic import BaseModel, Field
import uvicorn

PORT = int(os.getenv("MOCK_AGENT_PORT", "5050"))
AGENT_NAME = os.getenv("MOCK_AGENT_NAME", "Mock Echo Agent")


class ExecuteRequest(BaseModel):
    """Payload expected by /execute."""

    request: str = Field(..., description="Task description")
    context: Optional[Dict[str, Any]] = Field(default=None)
    metadata: Optional[Dict[str, Any]] = Field(default=None)


app = FastAPI(title=AGENT_NAME, version="1.0.0")


@app.get("/health")
async def health() -> Dict[str, str]:
    """Basic health probe."""
    return {"status": "ok", "agent": AGENT_NAME}


@app.post("/execute")
async def execute(payload: ExecuteRequest) -> Dict[str, Any]:
    """Echo request back with a mock success payload."""
    return {
        "success": True,
        "agent": AGENT_NAME,
        "received_at": datetime.utcnow().isoformat(),
        "result": {
            "summary": f"Processed request of length {len(payload.request)} characters.",
            "context": payload.context or {},
        },
        "metadata": payload.metadata or {},
    }


def main() -> None:
    """Launch the mock agent server."""
    uvicorn.run(
        app,
        host=os.getenv("MOCK_AGENT_HOST", "0.0.0.0"),
        port=PORT,
        log_level="info",
    )


if __name__ == "__main__":
    main()
