"""Agent search tools using Identity, Reputation, and Validation registries."""

import sys
import os
from typing import List, Dict, Any, Optional

from strands import tool

# Add shared to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from shared.handlers.identity_registry_handlers import (
    get_agent,
    resolve_by_domain,
    resolve_by_address,
    get_agent_count
)
from shared.handlers.reputation_registry_handlers import (
    is_feedback_authorized
)


class AgentSearcher:
    """Search and rank agents using ERC-8004 registries."""

    def __init__(self):
        pass

    def get_agent_by_id(self, agent_id: int) -> Optional[Dict[str, Any]]:
        """Retrieve agent details from identity registry."""
        try:
            agent = get_agent(agent_id)
            if agent:
                return {
                    "agent_id": agent_id,
                    "domain": agent[0],
                    "address": agent[1],
                    "exists": True
                }
            return None
        except Exception as e:
            print(f"Error getting agent {agent_id}: {e}")
            return None

    def get_agent_by_domain(self, domain: str) -> Optional[Dict[str, Any]]:
        """Resolve agent by domain name."""
        try:
            agent = resolve_by_domain(domain)
            if agent:
                return {
                    "domain": agent[0],
                    "address": agent[1],
                    "exists": agent[0] != ""
                }
            return None
        except Exception as e:
            print(f"Error resolving domain {domain}: {e}")
            return None

    def get_agent_reputation_score(self, agent_client_id: int, agent_server_id: int) -> Dict[str, Any]:
        """Check if feedback is authorized between two agents (reputation indicator)."""
        try:
            result = is_feedback_authorized(agent_client_id, agent_server_id)
            return {
                "has_reputation": result.get("authorized", False),
                "feedback_auth_id": result.get("feedback_auth_id")
            }
        except Exception as e:
            print(f"Error getting reputation for agents {agent_client_id}, {agent_server_id}: {e}")
            return {"has_reputation": False, "feedback_auth_id": None}

    def calculate_relevance_score(
        self,
        agent: Dict[str, Any],
        search_criteria: Dict[str, Any]
    ) -> float:
        """
        Calculate relevance score based on multiple factors.

        Scoring factors:
        - Domain match (40 points)
        - Has reputation (30 points)
        - Agent exists and is active (20 points)
        - Address verification (10 points)
        """
        score = 0.0

        # Domain matching
        search_domain = search_criteria.get("domain", "").lower()
        agent_domain = agent.get("domain", "").lower()

        if search_domain and agent_domain:
            # Exact match
            if search_domain == agent_domain:
                score += 40
            # Partial match
            elif search_domain in agent_domain or agent_domain in search_domain:
                score += 25
            # Contains keywords
            elif any(keyword in agent_domain for keyword in search_domain.split()):
                score += 15

        # Reputation score
        if agent.get("has_reputation"):
            score += 30

        # Agent exists and is active
        if agent.get("exists"):
            score += 20

        # Valid address
        if agent.get("address") and agent["address"] != "0x0000000000000000000000000000000000000000":
            score += 10

        return score

    def get_all_agents(self) -> List[Dict[str, Any]]:
        """Retrieve all registered agents from the identity registry."""
        try:
            agent_count = get_agent_count()
            agents = []

            for agent_id in range(1, agent_count + 1):
                agent = self.get_agent_by_id(agent_id)
                if agent and agent.get("exists"):
                    agents.append(agent)

            return agents
        except Exception as e:
            print(f"Error getting all agents: {e}")
            return []

    def search_agents(
        self,
        domain: Optional[str] = None,
        address: Optional[str] = None,
        limit: int = 5
    ) -> List[Dict[str, Any]]:
        """
        Search for agents and return top N most relevant results.

        Args:
            domain: Domain keyword to search for
            address: Specific address to search for
            limit: Maximum number of results to return (default: 5)

        Returns:
            List of top N most relevant agents with their scores
        """
        search_criteria = {
            "domain": domain or "",
            "address": address or ""
        }

        # Get all agents
        all_agents = self.get_all_agents()

        # If searching by address, try direct lookup first
        if address:
            try:
                agent = resolve_by_address(address)
                if agent and agent[0]:  # domain exists
                    return [{
                        "domain": agent[0],
                        "address": agent[1],
                        "exists": True,
                        "relevance_score": 100.0,
                        "rank": 1
                    }]
            except Exception as e:
                print(f"Error resolving by address: {e}")

        # If searching by domain, try direct lookup first
        if domain:
            agent = self.get_agent_by_domain(domain)
            if agent and agent.get("exists"):
                agent["relevance_score"] = 100.0
                agent["rank"] = 1
                agent["has_reputation"] = False  # Can add reputation check here
                return [agent]

        # Score all agents
        scored_agents = []
        for agent in all_agents:
            # Add reputation data if available
            agent_id = agent.get("agent_id")
            if agent_id:
                # Check reputation with a reference agent (could be parameterized)
                rep_data = self.get_agent_reputation_score(agent_id, agent_id)
                agent["has_reputation"] = rep_data["has_reputation"]

            score = self.calculate_relevance_score(agent, search_criteria)
            agent["relevance_score"] = score
            scored_agents.append(agent)

        # Sort by score descending
        scored_agents.sort(key=lambda x: x["relevance_score"], reverse=True)

        # Take top N and add rank
        top_agents = scored_agents[:limit]
        for idx, agent in enumerate(top_agents, 1):
            agent["rank"] = idx

        return top_agents


# Convenience functions for tool integration

@tool
async def search_agents_by_domain(domain: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Search for agents by domain and return top N most relevant results.

    Args:
        domain: Domain keyword to search for (e.g., "data-analysis", "trading", "oracle")
        limit: Maximum number of results to return (default: 5)

    Returns:
        List of top N most relevant agents with metadata and relevance scores

    Example:
        agents = await search_agents_by_domain("trading", limit=5)
        # Returns: [
        #     {"rank": 1, "domain": "trading-bot", "address": "0x...", "relevance_score": 85.0, ...},
        #     {"rank": 2, "domain": "crypto-trading", "address": "0x...", "relevance_score": 70.0, ...}
        # ]
    """
    searcher = AgentSearcher()
    return searcher.search_agents(domain=domain, limit=limit)


@tool
async def search_agents_by_address(address: str) -> Dict[str, Any]:
    """
    Find agent by wallet address.

    Args:
        address: Ethereum address of the agent

    Returns:
        Agent metadata if found, None otherwise

    Example:
        agent = await search_agents_by_address("0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb")
        # Returns: {"domain": "trading-bot", "address": "0x...", "exists": True, ...}
    """
    searcher = AgentSearcher()
    results = searcher.search_agents(address=address, limit=1)
    return results[0] if results else None


@tool
async def find_top_agents(
    domain: Optional[str] = None,
    include_reputation: bool = True,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Find top N agents based on comprehensive scoring.

    Args:
        domain: Optional domain filter
        include_reputation: Whether to include reputation in scoring (default: True)
        limit: Maximum number of results (default: 5)

    Returns:
        List of top agents with detailed metadata and scoring breakdown

    Example:
        top_agents = await find_top_agents(domain="oracle", limit=3)
        # Returns ranked list with relevance scores
    """
    searcher = AgentSearcher()
    results = searcher.search_agents(domain=domain, limit=limit)

    # Add additional metadata
    for agent in results:
        # If reputation should not be included, remove it from scoring
        if not include_reputation:
            agent["has_reputation"] = False
            # Recalculate score without reputation
            if agent.get("relevance_score", 0) >= 30:
                agent["relevance_score"] -= 30

        agent["scoring_breakdown"] = {
            "domain_match": "Exact" if agent["relevance_score"] >= 60 else "Partial" if agent["relevance_score"] >= 40 else "Low",
            "has_reputation": agent.get("has_reputation", False),
            "is_active": agent.get("exists", False),
            "total_score": agent["relevance_score"]
        }

    return results


@tool
async def get_agent_details_by_id(agent_id: int) -> Dict[str, Any]:
    """
    Get complete agent details by ID including reputation data.

    Args:
        agent_id: Agent ID in the identity registry

    Returns:
        Complete agent profile with identity and reputation data

    Example:
        details = await get_agent_details_by_id(42)
        # Returns: {"agent_id": 42, "domain": "...", "address": "...", ...}
    """
    searcher = AgentSearcher()
    agent = searcher.get_agent_by_id(agent_id)

    if agent:
        # Add reputation data
        rep_data = searcher.get_agent_reputation_score(agent_id, agent_id)
        agent.update(rep_data)

    return agent
