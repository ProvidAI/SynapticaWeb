"""Health check utilities for ProvidAI system components."""

import logging
import os
from typing import Dict, Any
import httpx

logger = logging.getLogger(__name__)

# Research API configuration
RESEARCH_API_BASE_URL = os.getenv("RESEARCH_API_URL", "http://localhost:5000")
HEALTH_CHECK_TIMEOUT = int(os.getenv("HEALTH_CHECK_TIMEOUT", "5"))  # seconds


async def check_research_api_health() -> Dict[str, Any]:
    """
    Check if research agents API is reachable and healthy.

    Returns:
        Dict with:
        - healthy (bool): True if API is accessible
        - error (str): Error message if unhealthy
        - troubleshooting (list): Steps to fix if unhealthy
        - response_time (float): API response time in seconds
    """
    try:
        import time
        start_time = time.time()

        async with httpx.AsyncClient(timeout=HEALTH_CHECK_TIMEOUT) as client:
            # Try health endpoint first
            try:
                response = await client.get(f"{RESEARCH_API_BASE_URL}/health")
                response_time = time.time() - start_time

                if response.status_code == 200:
                    logger.info(f"[health_check] Research API healthy ({response_time:.2f}s)")
                    return {
                        "healthy": True,
                        "response_time": response_time,
                        "url": RESEARCH_API_BASE_URL
                    }
            except httpx.HTTPError:
                # Health endpoint might not exist, try agents list endpoint
                response = await client.get(f"{RESEARCH_API_BASE_URL}/agents")
                response_time = time.time() - start_time

                if response.status_code == 200:
                    logger.info(f"[health_check] Research API healthy via /agents ({response_time:.2f}s)")
                    return {
                        "healthy": True,
                        "response_time": response_time,
                        "url": RESEARCH_API_BASE_URL,
                        "note": "Health endpoint not available, used /agents instead"
                    }

        # If we get here, neither endpoint worked
        raise Exception("No accessible endpoints")

    except httpx.ConnectError as e:
        logger.warning(f"[health_check] Research API connection failed: {e}")
        return {
            "healthy": False,
            "error": "Cannot connect to research agents API",
            "root_cause": f"Connection refused to {RESEARCH_API_BASE_URL}",
            "troubleshooting": [
                f"Start research agents server: ./start_research_agents.sh",
                f"Check if port 5000 or 5001 is available",
                f"Verify RESEARCH_API_URL environment variable is correct: {RESEARCH_API_BASE_URL}",
                f"Test connectivity: curl {RESEARCH_API_BASE_URL}/health"
            ]
        }

    except httpx.TimeoutException:
        logger.warning(f"[health_check] Research API health check timed out after {HEALTH_CHECK_TIMEOUT}s")
        return {
            "healthy": False,
            "error": f"Research agents API not responding (timeout after {HEALTH_CHECK_TIMEOUT}s)",
            "root_cause": "API is too slow or unresponsive",
            "troubleshooting": [
                "Check if research agents server is overloaded",
                "Restart research agents server",
                f"Increase HEALTH_CHECK_TIMEOUT (currently {HEALTH_CHECK_TIMEOUT}s)"
            ]
        }

    except Exception as e:
        logger.error(f"[health_check] Unexpected error checking research API health: {e}")
        return {
            "healthy": False,
            "error": f"Health check failed: {str(e)}",
            "root_cause": "Unexpected error during health check",
            "troubleshooting": [
                "Check research agents server logs for errors",
                "Verify network connectivity",
                "Try restarting research agents server"
            ]
        }


async def check_agent_registry_health() -> Dict[str, Any]:
    """
    Check if agent registry (blockchain) is accessible.

    Returns:
        Dict with:
        - healthy (bool): True if registry is accessible
        - agent_count (int): Number of registered agents
        - min_agents_met (bool): True if >= 2 agents available
        - error (str): Error message if unhealthy
        - troubleshooting (list): Steps to fix if unhealthy
    """
    try:
        from shared.handlers.identity_registry_handlers import get_all_domains

        domains = get_all_domains()
        agent_count = len(domains)

        logger.info(f"[health_check] Agent registry healthy, {agent_count} agents registered")

        return {
            "healthy": True,
            "agent_count": agent_count,
            "min_agents_met": agent_count >= 2,
            "agents": domains[:5],  # First 5 for preview
            "warning": "Only 1 agent available - no fallback option" if agent_count == 1 else None
        }

    except RuntimeError as e:
        logger.error(f"[health_check] Registry not initialized: {e}")
        return {
            "healthy": False,
            "agent_count": 0,
            "min_agents_met": False,
            "error": "Identity registry not initialized",
            "root_cause": str(e),
            "troubleshooting": [
                "Verify HEDERA_EVM_RPC_URL is set correctly",
                "Check if Hedera testnet is accessible",
                "Verify identity registry contract is deployed",
                "Check IDENTITY_REGISTRY_ADDRESS environment variable"
            ]
        }

    except Exception as e:
        logger.error(f"[health_check] Error checking registry health: {e}")
        return {
            "healthy": False,
            "agent_count": 0,
            "min_agents_met": False,
            "error": f"Registry health check failed: {str(e)}",
            "root_cause": "Error accessing blockchain registry",
            "troubleshooting": [
                "Check blockchain RPC connectivity",
                "Verify smart contract addresses",
                "Check for blockchain network issues"
            ]
        }


async def get_system_health() -> Dict[str, Any]:
    """
    Get comprehensive system health status.

    Returns:
        Dict with health status of all components:
        - status: "healthy", "degraded", or "unhealthy"
        - research_api: Research API health details
        - registry: Agent registry health details
        - timestamp: Current timestamp
    """
    import datetime

    # Check all components
    research_api_health = await check_research_api_health()
    registry_health = await check_agent_registry_health()

    # Determine overall system status
    if research_api_health["healthy"] and registry_health["healthy"] and registry_health["min_agents_met"]:
        status = "healthy"
    elif research_api_health["healthy"] or registry_health["healthy"]:
        status = "degraded"
    else:
        status = "unhealthy"

    return {
        "status": status,
        "research_api": research_api_health,
        "registry": registry_health,
        "timestamp": datetime.datetime.now().isoformat(),
        "issues": [
            issue for issue in [
                "Research API unavailable" if not research_api_health["healthy"] else None,
                "Agent registry unavailable" if not registry_health["healthy"] else None,
                "Insufficient agents (need >= 2)" if not registry_health.get("min_agents_met") else None
            ] if issue is not None
        ]
    }
