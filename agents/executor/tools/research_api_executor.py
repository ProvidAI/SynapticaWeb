"""Research API executor - calls research agents via FastAPI server on port 5001."""

import json
import logging
import os
from typing import Any, Dict, Optional

import httpx
from strands import tool

from shared.task_progress import update_progress

logger = logging.getLogger(__name__)

# Research agents API base URL
RESEARCH_API_BASE_URL = os.getenv("RESEARCH_API_URL")


@tool
async def list_research_agents() -> Dict[str, Any]:
    """
    List all available research agents from the FastAPI server.

    Returns:
        Dict with list of available agents, their capabilities, and pricing:
        {
            "success": bool,
            "total_agents": int,
            "agents": [
                {
                    "agent_id": str,
                    "name": str,
                    "description": str,
                    "capabilities": List[str],
                    "pricing": dict,
                    "endpoint": str,
                    "reputation_score": float
                }
            ]
        }
    """
    try:
        logger.info(f"[list_research_agents] Fetching agents from {RESEARCH_API_BASE_URL}/agents")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RESEARCH_API_BASE_URL}/agents")
            response.raise_for_status()

            data = response.json()
            logger.info(f"[list_research_agents] Found {data.get('total_agents', 0)} agents")

            return {
                "success": True,
                **data
            }

    except httpx.HTTPError as e:
        logger.error(f"[list_research_agents] HTTP error: {e}")
        return {
            "success": False,
            "error": f"Failed to connect to research agents API: {str(e)}",
            "suggestion": "Make sure the research agents server is running on port 5001"
        }
    except Exception as e:
        logger.error(f"[list_research_agents] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }


@tool
async def execute_research_agent(
    agent_domain: str,
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Execute a research agent via the FastAPI server.

    This function makes a real HTTP POST request to the research agents API
    running on port 5001. No simulation - actual agent execution.

    Args:
        agent_domain: The agent domain (e.g., "feasibility-analyst-001", "literature-miner-001")
        task_description: Description of the task to execute
        context: Optional context dict with additional parameters (budget, timeline, etc.)
        metadata: Optional metadata (task_id, user_id, etc.)

    Returns:
        Dict with execution results:
        {
            "success": bool,
            "agent_id": str,
            "result": Any,  # The actual agent output
            "error": str (if failed),
            "metadata": dict
        }

    Example:
        result = await execute_research_agent(
            agent_id="feasibility-analyst-001",
            task_description="Analyze feasibility of building a blockchain analytics platform",
            context={"budget": "5000 HBAR", "timeline": "3 months"},
            metadata={"task_id": "task-123"}
        )
    """
    try:
        logger.info(f"[execute_research_agent] Executing agent: {agent_domain}")
        logger.info(f"[execute_research_agent] Task: {task_description[:100]}...")

        if isinstance(context, str):
            try:
                context = json.loads(context)
            except json.JSONDecodeError:
                raise ValueError(f"context string is not valid JSON: {context}")

        if isinstance(metadata, str):
            try:
                metadata = json.loads(metadata)
            except json.JSONDecodeError:
                raise ValueError(f"metadata string is not valid JSON: {metadata}")

        # Construct request payload
        payload = {
            "request": task_description,
            "context": context or {},
            "metadata": metadata or {}
        }
        logger.info(f"[execute_research_agent] Payload: {payload}")

        endpoint = f"{RESEARCH_API_BASE_URL}/agents/{agent_domain}"
        logger.info(f"[execute_research_agent] Calling {endpoint}")

        # Emit web_search progress if this is a literature/web search agent and we have a task_id
        try:
            task_id = (metadata or {}).get("task_id")
            if task_id and any(k in (agent_domain or "") for k in ("literature", "miner", "knowledge", "paper", "search")):
                update_progress(task_id, "web_search", "running", {
                    "message": "Searching the web for relevant sources",
                    "agent_domain": agent_domain
                })
        except Exception:
            # Non-fatal; continue execution
            pass

        async with httpx.AsyncClient(timeout=120.0) as client:  # 2 minute timeout for agent execution
            response = await client.post(endpoint, json=payload)
            response.raise_for_status()

            data = response.json()
            logger.info(f"[execute_research_agent] Agent execution {'succeeded' if data.get('success') else 'failed'}")

            if not data.get("success"):
                logger.error(f"[execute_research_agent] Agent returned error: {data.get('error')}")

            # Close web_search phase if it was opened
            try:
                task_id = (metadata or {}).get("task_id")
                if task_id and any(k in (agent_domain or "") for k in ("literature", "miner", "knowledge", "paper", "search")):
                    update_progress(task_id, "web_search", "completed", {
                        "message": "✓ Web search results retrieved",
                        "agent_domain": agent_domain
                    })
            except Exception:
                pass

            return data

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            logger.error(f"[execute_research_agent] Agent not found: {agent_domain}")
            return {
                "success": False,
                "agent_id": agent_domain,
                "error": f"Agent '{agent_domain}' not found. Use list_research_agents to see available agents.",
            }
        else:
            logger.error(f"[execute_research_agent] HTTP {e.response.status_code}: {e}")
            return {
                "success": False,
                "agent_id": agent_domain,
                "error": f"HTTP error {e.response.status_code}: {str(e)}",
            }

    except httpx.TimeoutException:
        logger.error(f"[execute_research_agent] Request timed out for agent: {agent_domain}")
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": "Agent execution timed out (120s limit). The task may be too complex.",
        }

    except httpx.HTTPError as e:
        logger.error(f"[execute_research_agent] HTTP error: {e}")
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": f"Failed to connect to research agents API: {str(e)}",
            "suggestion": "Make sure the research agents server is running on port 5001"
        }

    except Exception as e:
        logger.error(f"[execute_research_agent] Unexpected error: {e}", exc_info=True)
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": f"Unexpected error: {str(e)}",
        }


@tool
async def get_agent_metadata(agent_id: str) -> Dict[str, Any]:
    """
    Get detailed metadata for a specific research agent.

    Args:
        agent_id: The agent ID (e.g., "feasibility-analyst-001")

    Returns:
        Dict with agent metadata including capabilities, pricing, API spec, etc.
    """
    try:
        logger.info(f"[get_agent_metadata] Fetching metadata for: {agent_id}")

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{RESEARCH_API_BASE_URL}/agents/{agent_id}")
            response.raise_for_status()

            data = response.json()
            logger.info(f"[get_agent_metadata] Retrieved metadata for {agent_id}")

            return {
                "success": True,
                **data
            }

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            return {
                "success": False,
                "error": f"Agent '{agent_id}' not found"
            }
        else:
            return {
                "success": False,
                "error": f"HTTP error {e.response.status_code}: {str(e)}"
            }

    except Exception as e:
        logger.error(f"[get_agent_metadata] Error: {e}", exc_info=True)
        return {
            "success": False,
            "error": str(e)
        }
