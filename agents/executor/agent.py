"""Executor Agent implementation with meta-tooling capabilities."""

import os
from shared.openai_agent import Agent, create_openai_agent

from .system_prompt import EXECUTOR_SYSTEM_PROMPT
from .tools import (
    create_dynamic_tool,
    load_and_execute_tool,
    list_dynamic_tools,
    execute_shell_command,
    get_tool_template,
)


def create_executor_agent() -> Agent:
    """
    Create and configure the Executor agent with meta-tooling capabilities.

    The Executor agent is the KEY INNOVATION in this architecture:
    - It dynamically creates tools at runtime
    - Uses load_tool to integrate discovered marketplace agents
    - Demonstrates meta-tooling pattern for agent composition

    Returns:
        Configured OpenAI Agent instance
    """
    api_key = os.getenv("OPENAI_API_KEY")
    model = os.getenv("EXECUTOR_MODEL", "gpt-4-turbo-preview")

    if not api_key:
        raise ValueError("OPENAI_API_KEY not set")

    # Core tools for meta-tooling
    tools = [
        create_dynamic_tool,  # Generate new tools at runtime
        load_and_execute_tool,  # Load and run generated tools
        list_dynamic_tools,  # List available tools
        execute_shell_command,  # Shell operations
        get_tool_template,  # Get templates for tool creation
    ]

    agent = create_openai_agent(
        api_key=api_key,
        model=model,
        system_prompt=EXECUTOR_SYSTEM_PROMPT,
        tools=tools,
    )

    return agent


# Example usage demonstrating meta-tooling
async def run_executor_meta_tooling_example():
    """
    Example demonstrating the meta-tooling pattern.

    This shows how the Executor dynamically creates and uses tools.
    """
    agent = create_executor_agent()

    # Step 1: Receive agent metadata (normally from Negotiator)
    agent_metadata = {
        "agent_id": "data-analyzer-001",
        "name": "Sales Data Analyzer",
        "endpoint": "https://api.example.com/analyze",
        "capabilities": ["data-analysis", "forecasting"],
    }

    tool_spec = {
        "endpoint": "https://api.example.com/analyze",
        "method": "POST",
        "parameters": [
            {"name": "data", "type": "str", "description": "CSV data to analyze"},
            {"name": "analysis_type", "type": "str", "description": "Type of analysis"},
        ],
        "auth_type": "bearer",
        "description": "Analyze sales data and generate insights",
    }

    # Step 2: Ask agent to create and use the tool
    request = f"""
    Create a dynamic tool for the following marketplace agent:

    Agent: {agent_metadata['name']}
    Endpoint: {tool_spec['endpoint']}

    Tool specification:
    {tool_spec}

    Then use the created tool to analyze this sample data:
    "date,sales\\n2024-01-01,1000\\n2024-01-02,1200"

    Analysis type: "trends"
    """

    result = await agent.run(request)
    print("Meta-tooling result:")
    print(result)


if __name__ == "__main__":
    import asyncio

    asyncio.run(run_executor_meta_tooling_example())
