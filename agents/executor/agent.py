"""Executor Agent implementation - executes research agents via API."""

import os

from agents.executor.tools.research_api_executor import (
    execute_research_agent,
    get_agent_metadata,
    list_research_agents,
)
from shared.openai_agent import Agent, create_openai_agent

from .system_prompt import EXECUTOR_SYSTEM_PROMPT


def create_executor_agent() -> Agent:
    """
    Create and configure the Executor agent.

    The Executor agent:
    - Lists available research agents from the API server (port 5001)
    - Selects the best agent for each microtask
    - Executes agents via HTTP POST requests (no simulation)
    - Returns real agent outputs

    Returns:
        Configured OpenAI Agent instance
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("EXECUTOR_MODEL", "gpt-4-turbo-preview")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Tools for executing research agents via API
    tools = [
        list_research_agents,      # List all available research agents
        execute_research_agent,    # Execute a specific research agent
        get_agent_metadata,        # Get detailed agent metadata
    ]

    agent = create_openai_agent(
        api_key=api_key,
        model=model, 
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
        tools=tools,
    )

    return agent
