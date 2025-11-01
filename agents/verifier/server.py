"""Expose the Verifier agent over the lightweight A2A HTTP transport."""

from __future__ import annotations

import logging
import os

from shared.a2a import A2AServer, AgentCapability, AgentCard

from .agent import create_verifier_agent

logger = logging.getLogger(__name__)


def build_server() -> A2AServer:
    """Construct an A2A server instance for the Verifier agent."""

    agent = create_verifier_agent()
    agent_card = AgentCard(
        id=os.getenv("VERIFIER_A2A_ID", "verifier-agent"),
        name="Verifier Agent",
        description="Validates task results, executes verification logic, and manages escrow release.",
        version=os.getenv("VERIFIER_VERSION", "0.1.0"),
        capabilities=[
            AgentCapability(
                name="task-verification",
                description="Evaluates task results against schema, quality benchmarks, and verification criteria.",
            ),
            AgentCapability(
                name="payment-controls",
                description="Releases or rejects escrow payments based on verification outcomes.",
            ),
        ],
        tags=["verifier", "quality", "escrow", "a2a"],
    )

    host = os.getenv("VERIFIER_A2A_HOST", "0.0.0.0")
    port = int(os.getenv("VERIFIER_A2A_PORT", "9103"))

    return A2AServer(
        agent=agent,
        agent_card=agent_card,
        host=host,
        port=port,
    )


def serve() -> None:
    """Run the Verifier agent server."""

    server = build_server()
    logger.info(
        "Starting Verifier A2A server at %s:%s",
        server.host,
        server.port,
    )
    server.serve()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    serve()
