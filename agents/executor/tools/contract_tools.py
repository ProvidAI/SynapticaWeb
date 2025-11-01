"""Tools for Executor agent to query agents from smart contract registry."""

import os
import sys
from typing import Any, Dict, List, Optional

from strands import tool

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from shared.database.database import SessionLocal
from shared.database.models import Agent as AgentModel
from shared.handlers.identity_registry_handlers import (
    get_agent,
    get_agent_count,
    get_domains_paginated,
    resolve_by_domain,
)


@tool
async def query_agent_by_id(agent_id: int) -> Dict[str, Any]:
    """
    Query an agent from the smart contract registry by agent ID.

    Args:
        agent_id: The agent ID (uint256) from the Identity Registry contract

    Returns:
        Dictionary with agent information:
        {
            "agent_id": int,
            "domain": str,
            "address": str,
            "on_chain": true
        }
    """
    try:
        agent_data = get_agent(agent_id)
        if not agent_data:
            return {"success": False, "error": f"Agent {agent_id} not found"}

        return {
            "success": True,
            "agent_id": agent_data[0],
            "domain": agent_data[1],
            "address": agent_data[2],
            "on_chain": True,
        }
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def query_agent_by_domain(domain: str) -> Dict[str, Any]:
    """
    Query an agent from the smart contract registry by domain name.

    Args:
        domain: The agent domain name (e.g., "problem-framer-001")

    Returns:
        Dictionary with agent information including API endpoint metadata if available
    """
    try:
        agent_data = resolve_by_domain(domain)
        if not agent_data:
            return {"success": False, "error": f"Agent with domain '{domain}' not found"}

        agent_id = agent_data[0]
        agent_domain = agent_data[1]
        agent_address = agent_data[2]

        # Try to get API endpoint from database
        db = SessionLocal()
        try:
            db_agent = db.query(AgentModel).filter(AgentModel.agent_id == domain).first()
            api_endpoint = None
            if db_agent and db_agent.meta:
                api_endpoint = db_agent.meta.get("api_endpoint")
        except Exception:
            db_agent = None
            api_endpoint = None
        finally:
            db.close()

        result = {
            "success": True,
            "agent_id": agent_id,
            "domain": agent_domain,
            "address": agent_address,
            "on_chain": True,
        }

        if api_endpoint:
            result["api_endpoint"] = api_endpoint
        elif db_agent:
            # Try to construct endpoint from domain or use metadata URI
            if db_agent.erc8004_metadata_uri:
                result["metadata_uri"] = db_agent.erc8004_metadata_uri
            # Could construct endpoint from domain if there's a convention
            # For now, return what we have

        return result
    except Exception as e:
        return {"success": False, "error": str(e)}


@tool
async def list_all_agents(offset: int = 0, limit: int = 100) -> Dict[str, Any]:
    """
    List all agents registered on the smart contract registry.

    This function tries to use getDomainsPaginated if available, otherwise
    it queries agents by iterating through agent IDs.

    Args:
        offset: Starting index for pagination (default: 0)
        limit: Maximum number of agents to return (default: 100, max: 1000)

    Returns:
        Dictionary with paginated list of agents:
        {
            "agents": [
                {
                    "agent_id": int,
                    "domain": str,
                    "address": str
                },
                ...
            ],
            "total": int,
            "offset": int,
            "limit": int
        }
    """
    try:
        # Try to use paginated domain listing first
        try:
            domains_result = get_domains_paginated(offset, limit)
            
            agents = []
            for domain in domains_result.get("domains", []):
                try:
                    agent_data = resolve_by_domain(domain)
                    if agent_data:
                        agents.append({
                            "agent_id": agent_data[0],
                            "domain": agent_data[1],
                            "address": agent_data[2],
                        })
                except Exception:
                    continue  # Skip domains that fail to resolve

            return {
                "success": True,
                "agents": agents,
                "total": domains_result.get("total", 0),
                "offset": offset,
                "limit": limit,
            }
        except Exception:
            # Fallback: iterate through agent IDs
            # This is less efficient but works if getDomainsPaginated doesn't exist
            total_count = get_agent_count()
            agents = []
            
            start_id = offset + 1  # Agent IDs start at 1
            end_id = min(start_id + limit, total_count + 1)
            
            for agent_id in range(start_id, end_id):
                try:
                    agent_data = get_agent(agent_id)
                    if agent_data:
                        agents.append({
                            "agent_id": agent_data[0],
                            "domain": agent_data[1],
                            "address": agent_data[2],
                        })
                except Exception:
                    continue  # Skip agents that don't exist
            
            return {
                "success": True,
                "agents": agents,
                "total": total_count,
                "offset": offset,
                "limit": limit,
            }
    except Exception as e:
        return {"success": False, "error": str(e), "agents": []}


@tool
async def get_agent_metadata_for_execution(agent_id: Optional[int] = None, domain: Optional[str] = None) -> Dict[str, Any]:
    """
    Get complete agent metadata including API endpoint for creating dynamic tools.

    This function queries the smart contract for agent identity and then
    tries to find the API endpoint from the database.

    Args:
        agent_id: Agent ID from the contract (optional, use either agent_id or domain)
        domain: Agent domain name (optional, use either agent_id or domain)

    Returns:
        Complete agent metadata including:
        {
            "agent_id": int,
            "domain": str,
            "address": str,
            "api_endpoint": str (if available),
            "capabilities": List[str] (if available),
            "tool_spec": Dict (if available)
        }
    """
    try:
        # Query contract
        agent_data = None
        if agent_id:
            agent_data = get_agent(agent_id)
            if agent_data:
                domain = agent_data[1]  # Extract domain for DB lookup
        elif domain:
            agent_data = resolve_by_domain(domain)
        
        if not agent_data:
            return {
                "success": False,
                "error": f"Agent not found (agent_id={agent_id}, domain={domain})"
            }

        contract_agent_id = agent_data[0]
        contract_domain = agent_data[1]
        contract_address = agent_data[2]

        # Query database for additional metadata
        db = SessionLocal()
        try:
            db_agent = db.query(AgentModel).filter(AgentModel.agent_id == contract_domain).first()
            
            result = {
                "success": True,
                "agent_id": contract_agent_id,
                "domain": contract_domain,
                "address": contract_address,
                "on_chain": True,
            }

            if db_agent:
                result["name"] = db_agent.name
                result["capabilities"] = db_agent.capabilities or []
                result["description"] = db_agent.description

                # Get API endpoint from meta or construct it
                if db_agent.meta:
                    api_endpoint = db_agent.meta.get("api_endpoint")
                    if api_endpoint:
                        result["api_endpoint"] = api_endpoint
                        result["tool_spec"] = db_agent.meta.get("tool_spec")
                
                # If no endpoint in meta, check metadata URI
                if "api_endpoint" not in result and db_agent.erc8004_metadata_uri:
                    result["metadata_uri"] = db_agent.erc8004_metadata_uri
                    # Note: In a real implementation, you'd fetch metadata from the URI
                    # For now, we'll return the URI and let the executor handle it

        finally:
            db.close()

        return result

    except Exception as e:
        return {"success": False, "error": str(e)}

