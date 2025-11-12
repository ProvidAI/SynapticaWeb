"""Research API executor - calls research agents via FastAPI server on port 5000."""

import logging
import os
from typing import Any, Dict, Optional
import httpx
import json

from strands import tool

logger = logging.getLogger(__name__)

# Research agents API base URL
RESEARCH_API_BASE_URL = os.getenv("RESEARCH_API_URL", "http://localhost:5000")
MARKETPLACE_API_BASE_URL = (
    os.getenv("MARKETPLACE_API_URL")
    or os.getenv("BACKEND_API_URL")
    or os.getenv("ORCHESTRATOR_API_URL")
    or "http://localhost:8000"
)

AGENT_DIRECTORY_URL = f"{MARKETPLACE_API_BASE_URL.rstrip('/')}/api/agents"

# Simple in-memory cache for agent records to avoid repeated lookups
_agent_cache: Dict[str, Dict[str, Any]] = {}


def _legacy_agent_endpoint(agent_domain: str) -> str:
    """Fallback endpoint pointing at the legacy research API server."""
    return f"{RESEARCH_API_BASE_URL.rstrip('/')}/agents/{agent_domain}"


async def _fetch_agent_record(agent_id: str) -> Optional[Dict[str, Any]]:
    """Fetch agent metadata from the marketplace API with caching."""
    if agent_id in _agent_cache:
        return _agent_cache[agent_id]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(f"{AGENT_DIRECTORY_URL}/{agent_id}")
            if response.status_code == 404:
                return None
            response.raise_for_status()
            data = response.json()
            if isinstance(data, dict):
                _agent_cache[agent_id] = data
                return data
    except Exception as error:
        logger.debug("[fetch_agent_record] Failed to fetch agent %s: %s", agent_id, error)

    return None


async def _resolve_agent_endpoint(agent_domain: str, explicit_endpoint: Optional[str]) -> str:
    """
    Determine the best endpoint for executing the agent.

    Preference order:
    1. Explicit endpoint supplied via tool argument.
    2. Stored endpoint from marketplace metadata.
    3. Legacy research API fallback.
    """
    if explicit_endpoint:
        return explicit_endpoint

    record = await _fetch_agent_record(agent_domain)
    if record:
        endpoint_url = record.get("endpoint_url")
        if endpoint_url:
            return endpoint_url

    logger.debug(
        "[resolve_agent_endpoint] Falling back to legacy endpoint for %s", agent_domain
    )
    return _legacy_agent_endpoint(agent_domain)


@tool
async def list_research_agents() -> Dict[str, Any]:
    """
    List all available research agents from the marketplace API.

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
    logger.info("[list_research_agents] Fetching agents from %s", AGENT_DIRECTORY_URL)

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(AGENT_DIRECTORY_URL)
            response.raise_for_status()
            data = response.json()

        agents = data.get("agents", [])
        for agent in agents:
            agent_id = agent.get("agent_id")
            if agent_id:
                _agent_cache[agent_id] = agent

        total = data.get("total", len(agents))
        logger.info("[list_research_agents] Found %s agents", total)

        return {
            "success": True,
            "total_agents": total,
            "agents": agents,
        }

    except Exception as primary_error:
        logger.warning(
            "[list_research_agents] Marketplace API unavailable (%s). Falling back to %s.",
            primary_error,
            RESEARCH_API_BASE_URL,
        )

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.get(f"{RESEARCH_API_BASE_URL.rstrip('/')}/agents")
                response.raise_for_status()
                data = response.json()

            agents = data.get("agents", [])
            for agent in agents:
                agent_id = agent.get("agent_id")
                if agent_id and agent_id not in _agent_cache:
                    _agent_cache[agent_id] = agent

            return {
                "success": True,
                "total_agents": data.get("total_agents", len(agents)),
                "agents": agents,
                "source": "legacy",
            }

        except Exception as fallback_error:
            logger.error("[list_research_agents] Failed to fetch agents: %s", fallback_error, exc_info=True)
            return {
                "success": False,
                "error": "Failed to fetch agent directory",
                "details": str(fallback_error),
            }


@tool
async def execute_research_agent(
    agent_domain: str,
    task_description: str,
    context: Optional[Dict[str, Any]] = None,
    metadata: Optional[Dict[str, Any]] = None,
    endpoint_url: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Execute a research agent via its published HTTP endpoint.

    The endpoint is resolved from the marketplace metadata and falls back to the
    legacy research API dispatcher when required. No simulation - actual HTTP call.

    Args:
        agent_domain: The agent domain (e.g., "feasibility-analyst-001", "literature-miner-001")
        task_description: Description of the task to execute
        context: Optional context dict with additional parameters (budget, timeline, etc.)
        metadata: Optional metadata (task_id, user_id, etc.)
        endpoint_url: Optional explicit endpoint override for the agent

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

        endpoint = await _resolve_agent_endpoint(agent_domain, endpoint_url)
        logger.info(f"[execute_research_agent] Calling {endpoint}")

        async def _post(url: str) -> Dict[str, Any]:
            async with httpx.AsyncClient(timeout=120.0) as client:
                response = await client.post(url, json=payload)
                response.raise_for_status()
                data = response.json()
                logger.info(
                    "[execute_research_agent] Agent execution %s via %s",
                    "succeeded" if data.get("success") else "failed",
                    url,
                )
                if not data.get("success"):
                    logger.error("[execute_research_agent] Agent returned error: %s", data.get("error"))
                return data

        try:
            return await _post(endpoint)
        except httpx.RequestError as connection_error:
            fallback_endpoint = _legacy_agent_endpoint(agent_domain)
            if endpoint != fallback_endpoint:
                logger.warning(
                    "[execute_research_agent] Primary endpoint %s unreachable (%s). Falling back to %s",
                    endpoint,
                    connection_error,
                    fallback_endpoint,
                )
                try:
                    return await _post(fallback_endpoint)
                except Exception as fallback_exception:  # noqa: BLE001
                    logger.error(
                        "[execute_research_agent] Fallback endpoint %s also failed: %s",
                        fallback_endpoint,
                        fallback_exception,
                    )
                    raise
            raise

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 404:
            logger.error(f"[execute_research_agent] Agent not found: {agent_domain}")
            return {
                "success": False,
                "agent_id": agent_domain,
                "error": f"Agent '{agent_domain}' not found or endpoint returned 404.",
            }
        logger.error(f"[execute_research_agent] HTTP {status_code}: {exc}")
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": f"HTTP error {status_code}: {exc.response.text}",
        }

    except httpx.TimeoutException:
        logger.error(f"[execute_research_agent] Request timed out for agent: {agent_domain}")
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": "Agent execution timed out (120s limit). The task may be too complex or the endpoint is overloaded.",
        }

    except httpx.HTTPError as exc:
        logger.error(f"[execute_research_agent] HTTP error: {exc}")
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": f"Failed to connect to agent endpoint: {str(exc)}",
            "suggestion": "Verify the agent endpoint URL is reachable from the executor runtime.",
        }

    except Exception as exc:  # noqa: BLE001
        logger.error(f"[execute_research_agent] Unexpected error: {exc}", exc_info=True)
        return {
            "success": False,
            "agent_id": agent_domain,
            "error": f"Unexpected error: {str(exc)}",
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

        record = await _fetch_agent_record(agent_id)
        if record:
            return {
                "success": True,
                **record,
            }

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(_legacy_agent_endpoint(agent_id))
            response.raise_for_status()
            data = response.json()
            logger.info(f"[get_agent_metadata] Retrieved metadata for {agent_id} via legacy API")
            return {
                "success": True,
                **data,
                "source": "legacy",
            }

    except httpx.HTTPStatusError as exc:
        status_code = exc.response.status_code
        if status_code == 404:
            return {
                "success": False,
                "error": f"Agent '{agent_id}' not found",
            }
        return {
            "success": False,
            "error": f"HTTP error {status_code}: {exc.response.text}",
        }

    except Exception as error:
        logger.error(f"[get_agent_metadata] Error: {error}", exc_info=True)
        return {
            "success": False,
            "error": str(error),
        }
