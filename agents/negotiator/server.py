"""Expose the Negotiator agent over the lightweight A2A HTTP transport."""

from __future__ import annotations

import logging
import os

from shared.a2a import A2AServer, AgentCapability, AgentCard

from .agent import create_negotiator_agent

logger = logging.getLogger(__name__)


def build_server() -> A2AServer:
    """Construct an A2A server instance for the Negotiator agent."""

    agent = create_negotiator_agent()
    agent_card = AgentCard(
        id=os.getenv("NEGOTIATOR_A2A_ID", "negotiator-agent"),
        name="Negotiator Agent",
        description="Discovers ERC-8004 agents, negotiates pricing, and drafts x402 payment proposals.",
        version=os.getenv("NEGOTIATOR_VERSION", "0.1.0"),
        capabilities=[
            AgentCapability(
                name="agent-negotiation",
                description="Finds marketplace agents, compares reputation, and proposes engagement terms.",
            ),
            AgentCapability(
                name="payment-proposals",
                description="Creates x402 payment proposals and A2A payment messages.",
            ),
        ],
        tags=["negotiator", "erc8004", "x402", "a2a"],
    )

    host = os.getenv("NEGOTIATOR_A2A_HOST", "0.0.0.0")
    port = int(os.getenv("NEGOTIATOR_A2A_PORT", "9101"))

    return A2AServer(
        agent=agent,
        agent_card=agent_card,
        host=host,
        port=port,
    )


def serve() -> None:
    """Run the Negotiator agent server."""

    server = build_server()
    logger.info(
        "Starting Negotiator A2A server at %s:%s",
        server.host,
        server.port,
    )
    server.serve()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    serve()
