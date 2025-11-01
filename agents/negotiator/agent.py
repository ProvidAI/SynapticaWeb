"""Negotiator Agent implementation using OpenAI API."""

import os
from shared.openai_agent import Agent, create_openai_agent

from .system_prompt import NEGOTIATOR_SYSTEM_PROMPT
from .tools import (
    find_agents,
    resolve_agent_by_domain,
    compare_agent_scores,
    create_payment_request,
    get_payment_status,
)


def create_negotiator_agent() -> Agent:
    """
    Create and configure the Negotiator agent.

    Returns:
        Configured OpenAI Agent instance
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("NEGOTIATOR_MODEL", "gpt-4-turbo-preview")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    tools = [
        find_agents,
        resolve_agent_by_domain,
        compare_agent_scores,
        create_payment_request,
        get_payment_status,
    ]

    agent = create_openai_agent(
        api_key=api_key,
        model=model,
        system_prompt=NEGOTIATOR_SYSTEM_PROMPT,
        tools=tools,
    )

    return agent
