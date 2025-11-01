"""OpenAI Agent wrapper for compatibility with the system."""

import os
import json
from typing import Dict, Any, List, Optional, Callable
from openai import AsyncOpenAI
from datetime import datetime


class OpenAIAgent:
    """
    OpenAI-compatible agent wrapper that mimics Strands SDK interface.

    This class provides a similar interface to the Strands Agent class
    but uses OpenAI's API instead.
    """

    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        system_prompt: str = "",
        tools: Optional[List[Callable]] = None,
        temperature: float = 0.7,
    ):
        """
        Initialize OpenAI Agent.

        Args:
            api_key: OpenAI API key (or uses env var OPENAI_API_KEY)
            model: Model to use (gpt-4-turbo-preview, gpt-4, gpt-3.5-turbo)
            system_prompt: System prompt for the agent
            tools: List of tool functions (for function calling)
            temperature: Temperature for generation
        """
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key not provided or found in environment")

        self.client = AsyncOpenAI(api_key=self.api_key)
        self.model = model
        self.system_prompt = system_prompt
        self.tools = tools or []
        self.temperature = temperature

        # Convert tools to OpenAI function schema
        self.functions = self._convert_tools_to_functions()

    def _convert_tools_to_functions(self) -> List[Dict[str, Any]]:
        """
        Convert tool functions to OpenAI function calling schema.

        Returns:
            List of function schemas
        """
        functions = []
        for tool in self.tools:
            # Extract function metadata from docstring and annotations
            func_name = tool.__name__
            func_doc = tool.__doc__ or "No description"

            # Basic function schema
            function_schema = {
                "name": func_name,
                "description": func_doc.split("\n")[0].strip(),
                "parameters": {
                    "type": "object",
                    "properties": {},
                    "required": []
                }
            }

            # Try to extract parameters from function annotations
            if hasattr(tool, "__annotations__"):
                for param_name, param_type in tool.__annotations__.items():
                    if param_name != "return":
                        # Simplified type mapping
                        param_type_str = "string"
                        if param_type in [int, float]:
                            param_type_str = "number"
                        elif param_type == bool:
                            param_type_str = "boolean"
                        elif param_type in [list, List]:
                            param_type_str = "array"
                        elif param_type in [dict, Dict]:
                            param_type_str = "object"

                        function_schema["parameters"]["properties"][param_name] = {
                            "type": param_type_str,
                            "description": f"Parameter {param_name}"
                        }

            functions.append(function_schema)

        return functions

    async def run(self, user_input: str, **kwargs) -> str:
        """
        Run the agent with user input.

        Args:
            user_input: User's input/request
            **kwargs: Additional parameters

        Returns:
            Agent's response as string
        """
        messages = [
            {"role": "system", "content": self.system_prompt},
            {"role": "user", "content": user_input}
        ]

        try:
            # For research agents, we don't use function calling
            # Instead, we ask the LLM to generate JSON responses directly
            # This is simpler and works better for structured outputs
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=kwargs.get("max_tokens", 4096),
                response_format={"type": "json_object"} if kwargs.get("json_mode", False) else None
            )

            # Extract response
            message = response.choices[0].message

            # Return regular message
            return message.content or ""

        except Exception as e:
            return f"Error: {str(e)}"

    async def run_with_messages(self, messages: List[Dict[str, str]], **kwargs) -> str:
        """
        Run the agent with a list of messages (for continuing conversations).

        Args:
            messages: List of message dictionaries with 'role' and 'content'
            **kwargs: Additional parameters

        Returns:
            Agent's response as string
        """
        # Ensure system prompt is included
        if not any(msg["role"] == "system" for msg in messages):
            messages.insert(0, {"role": "system", "content": self.system_prompt})

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=self.temperature,
                max_tokens=kwargs.get("max_tokens", 4096)
            )

            return response.choices[0].message.content

        except Exception as e:
            return f"Error: {str(e)}"


class Agent:
    """
    Compatibility wrapper to match Strands SDK Agent interface exactly.

    This allows existing code to work without modification.
    """

    def __init__(
        self,
        client: Any = None,  # Ignored, we create our own
        api_key: Optional[str] = None,
        model: str = "gpt-4-turbo-preview",
        system_prompt: str = "",
        tools: Optional[List] = None
    ):
        """Initialize agent with Strands-like interface."""
        # Create OpenAI agent internally
        self._agent = OpenAIAgent(
            api_key=api_key,
            model=model,
            system_prompt=system_prompt,
            tools=tools
        )

    async def run(self, request: str) -> str:
        """Run agent with request."""
        return await self._agent.run(request)


# Helper function to create agent
def create_openai_agent(
    system_prompt: str,
    api_key: Optional[str] = None,
    tools: Optional[List] = None,
    model: Optional[str] = None
) -> Agent:
    """
    Create an OpenAI agent with the specified configuration.

    Args:
        system_prompt: System prompt for the agent
        tools: Optional list of tool functions
        model: Optional model override

    Returns:
        Configured Agent instance
    """
    model = model or os.getenv("ORCHESTRATOR_MODEL", "gpt-4-turbo-preview")
    return Agent(
        api_key=api_key,
        model=model,
        system_prompt=system_prompt,
        tools=tools
    )
