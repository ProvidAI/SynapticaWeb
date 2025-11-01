"""Expose the Executor agent over the lightweight A2A HTTP transport."""

from __future__ import annotations

import logging
import os

from shared.a2a import A2AServer, AgentCapability, AgentCard

from .agent import create_executor_agent

logger = logging.getLogger(__name__)


def build_server() -> A2AServer:
    """Construct an A2A server instance for the Executor agent."""

    agent = create_executor_agent()
    agent_card = AgentCard(
        id=os.getenv("EXECUTOR_A2A_ID", "executor-agent"),
        name="Executor Agent",
        description="Executes marketplace workflows using dynamically generated tools.",
        version=os.getenv("EXECUTOR_VERSION", "0.1.0"),
        capabilities=[
            AgentCapability(
                name="meta-tooling",
                description="Generates Python tools at runtime based on marketplace agent metadata.",
            ),
            AgentCapability(
                name="task-execution",
                description="Executes generated tools and orchestrates API interactions.",
            ),
        ],
        tags=["executor", "meta-tooling", "a2a"],
    )

    host = os.getenv("EXECUTOR_A2A_HOST", "0.0.0.0")
    port = int(os.getenv("EXECUTOR_A2A_PORT", "9102"))

    return A2AServer(
        agent=agent,
        agent_card=agent_card,
        host=host,
        port=port,
    )


def serve() -> None:
    """Run the Executor agent server."""

    server = build_server()
    logger.info(
        "Starting Executor A2A server at %s:%s",
        server.host,
        server.port,
    )
    server.serve()


if __name__ == "__main__":
    logging.basicConfig(level=os.getenv("LOG_LEVEL", "INFO"))
    serve()
