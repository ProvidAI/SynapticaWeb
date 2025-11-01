"""Orchestrator Agent implementation using OpenAI API."""

import os
from shared.openai_agent import Agent, create_openai_agent

from .system_prompt import ORCHESTRATOR_SYSTEM_PROMPT
from .tools import (
    create_task,
    create_todo_list,
    executor_agent,
    get_task,
    negotiator_agent,
    authorize_payment_request,
    update_task_status,
    update_todo_item,
    verifier_agent,
)


def create_orchestrator_agent() -> Agent:
    """
    Create and configure the Orchestrator agent.

    Returns:
        Configured OpenAI Agent instance
    """
    # Get API key and model from environment
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("ORCHESTRATOR_MODEL", "gpt-4-turbo-preview")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Define tools for the orchestrator
    tools = [
        create_task,
        update_task_status,
        get_task,
        create_todo_list,
        update_todo_item,
        negotiator_agent,
        authorize_payment_request,
        executor_agent,
        verifier_agent,
    ]

    # Create agent with OpenAI
    agent = create_openai_agent(
        api_key=api_key,
        model=model,
        system_prompt=ORCHESTRATOR_SYSTEM_PROMPT,
        tools=tools,
    )

    return agent
