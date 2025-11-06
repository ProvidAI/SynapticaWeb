"""Simplified agent search tools using Identity, Reputation, and Validation registries."""

import sys
import os
import logging
from typing import List, Dict, Any

from strands import tool

# Set up logging
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

# Add shared to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from shared.handlers.identity_registry_handlers import (
    get_agent,
    get_all_domains,
    resolve_by_domain,
)
from shared.handlers.reputation_registry_handlers import (
    get_full_reputation_info
)
from shared.handlers.validation_registry_handlers import (
    get_full_validation_info
)


@tool
async def find_agents(domain: str) -> Dict[str, Any]:
    """
    Search for agents by domain keyword in the Identity Registry.

    This tool retrieves all registered domains and uses AI to determine which ones
    are relevant to the search query. Only relevant domains are resolved.

    Args:
        domain: Domain keyword or description to search for (e.g., "trading", "oracle", "data analysis")

    Returns:
        Dictionary with all domains for AI filtering:
        {
            "all_domains": List[str],
            "search_query": str,
            "instruction": str
        }

    Example:
        agents = await find_agents("trading bots for cryptocurrency")
        # AI will identify relevant domains like "crypto-trading-bot", "trading-analytics", etc.
    """
    try:
        logger.info(f"[find_agents] Starting search for domain: '{domain}'")

        # Get all registered domains from the contract
        all_domains = get_all_domains()

        logger.info(f"[find_agents] Retrieved {len(all_domains) if all_domains else 0} domains from registry")
        logger.info(f"[find_agents] Domains: {all_domains}")

        if not all_domains:
            logger.warning(f"[find_agents] No domains found in registry for search query: '{domain}'")
            return {
                "all_domains": [],
                "search_query": domain,
                "instruction": "No domains found in the registry. The ERC-8004 registry may be empty or unreachable."
            }

        # Return all domains for AI to filter
        # The AI agent will receive this list and determine which are relevant
        # Then it will call resolve_by_domain for each relevant one
        logger.info(f"[find_agents] Successfully returning {len(all_domains)} domains for AI filtering")
        return {
            "all_domains": all_domains,
            "search_query": domain,
            "instruction": "Use AI to identify which domains are relevant to the search query, then resolve each relevant domain using resolve_by_domain."
        }

    except Exception as e:
        logger.error(f"[find_agents] Error searching for domain '{domain}': {e}", exc_info=True)
        return {
            "all_domains": [],
            "search_query": domain,
            "instruction": f"Error occurred while searching registry: {str(e)}"
        }


@tool
async def resolve_agent_by_domain(domain: str) -> Dict[str, Any]:
    """
    Resolve a specific domain to get agent information.

    Use this tool after find_agents() to get detailed info for relevant domains.

    Args:
        domain: Exact domain name to resolve

    Returns:
        {
            "agent_id": int,
            "domain": str,
            "address": str,
            "success": bool
        }

    Example:
        # After AI determines "crypto-trading-bot" is relevant
        agent = await resolve_agent_by_domain("crypto-trading-bot")
    """
    try:
        logger.info(f"[resolve_agent_by_domain] Resolving domain: '{domain}'")

        agent_data = resolve_by_domain(domain)

        if agent_data:
            logger.info(f"[resolve_agent_by_domain] Successfully resolved '{domain}' -> Agent ID: {agent_data[0]}, Address: {agent_data[2]}")
            return {
                "agent_id": agent_data[0],
                "domain": agent_data[1],
                "address": agent_data[2],
                "success": True
            }
        else:
            logger.warning(f"[resolve_agent_by_domain] Domain '{domain}' not found in registry or returned None")
            return {
                "agent_id": None,
                "domain": domain,
                "address": None,
                "success": False,
                "error": "Domain not found in registry"
            }

    except Exception as e:
        logger.error(f"[resolve_agent_by_domain] Error resolving domain '{domain}': {e}", exc_info=True)
        return {
            "agent_id": None,
            "domain": domain,
            "address": None,
            "success": False,
            "error": str(e)
        }


@tool
async def compare_agent_scores(agent_ids: List[int]) -> Dict[str, Any]:
    """
    Compare reputation and validation scores for multiple agents.

    This tool fetches reputation (upvotes/downvotes) and validation (score/count)
    data for the given agents, calculates quality scores, and ranks them.

    Quality Score Calculation (0-100):
    - Reputation (50 points max):
      * Net score (upvotes - downvotes): 0-30 points
      * Total votes (engagement): 0-20 points
    - Validation (50 points max):
      * Average validation score: 0-35 points
      * Validation count: 0-15 points

    Args:
        agent_ids: List of agent IDs to compare

    Returns:
        {
            "ranked_agents": [
                {
                    "agent_id": int,
                    "domain": str,
                    "address": str,
                    "rank": int,
                    "quality_score": float (0-100),
                    "reputation": {
                        "score": int (net upvotes - downvotes),
                        "upVotes": int,
                        "downVotes": int
                    },
                    "validation": {
                        "count": int,
                        "averageScore": int (0-100)
                    }
                },
                ...
            ],
            "best_agent": {...}  # Top ranked agent
        }

    Example:
        comparison = await compare_agent_scores([1, 2, 3])
        best = comparison["best_agent"]
    """
    try:
        logger.info(f"[compare_agent_scores] Starting comparison for {len(agent_ids)} agents: {agent_ids}")

        agents_with_scores = []

        for agent_id in agent_ids:
            try:
                logger.info(f"[compare_agent_scores] Processing agent ID: {agent_id}")

                # Get agent identity
                agent_data = get_agent(agent_id)
                if not agent_data:
                    logger.warning(f"[compare_agent_scores] Agent {agent_id} not found in identity registry, skipping")
                    continue

                logger.info(f"[compare_agent_scores] Agent {agent_id} identity: domain='{agent_data[1]}', address={agent_data[2]}")

                # Get reputation data
                try:
                    rep_info = get_full_reputation_info(agent_id)
                    if not rep_info:
                        logger.warning(f"[compare_agent_scores] No reputation data for agent {agent_id}, using defaults")
                        rep_info = {"reputationScore": 0, "upVotes": 0, "downVotes": 0}
                    else:
                        logger.info(f"[compare_agent_scores] Agent {agent_id} reputation: score={rep_info['reputationScore']}, upVotes={rep_info['upVotes']}, downVotes={rep_info['downVotes']}")
                except RuntimeError as e:
                    logger.warning(f"[compare_agent_scores] Reputation registry unavailable for agent {agent_id}: {e}, using defaults")
                    rep_info = {"reputationScore": 0, "upVotes": 0, "downVotes": 0}

                # Get validation data
                try:
                    val_info = get_full_validation_info(agent_id)
                    if not val_info:
                        logger.warning(f"[compare_agent_scores] No validation data for agent {agent_id}, using defaults")
                        val_info = {"validationCount": 0, "averageScore": 0}
                    else:
                        logger.info(f"[compare_agent_scores] Agent {agent_id} validation: count={val_info['validationCount']}, avgScore={val_info['averageScore']}")
                except RuntimeError as e:
                    logger.warning(f"[compare_agent_scores] Validation registry unavailable for agent {agent_id}: {e}, using defaults")
                    val_info = {"validationCount": 0, "averageScore": 0}

                # Calculate quality score
                quality_score = calculate_quality_score(rep_info, val_info)
                logger.info(f"[compare_agent_scores] Agent {agent_id} quality score: {quality_score}/100")

                agents_with_scores.append({
                    "agent_id": agent_data[0],
                    "domain": agent_data[1],
                    "address": agent_data[2],
                    "quality_score": quality_score,
                    "reputation": {
                        "score": rep_info["reputationScore"],
                        "upVotes": rep_info["upVotes"],
                        "downVotes": rep_info["downVotes"]
                    },
                    "validation": {
                        "count": val_info["validationCount"],
                        "averageScore": val_info["averageScore"]
                    }
                })

            except Exception as e:
                logger.error(f"[compare_agent_scores] Error processing agent {agent_id}: {e}", exc_info=True)
                continue

        # Sort by quality score (descending)
        agents_with_scores.sort(key=lambda x: x["quality_score"], reverse=True)

        # Add ranks
        for idx, agent in enumerate(agents_with_scores, 1):
            agent["rank"] = idx

        logger.info(f"[compare_agent_scores] Successfully ranked {len(agents_with_scores)} agents")
        if agents_with_scores:
            logger.info(f"[compare_agent_scores] Best agent: ID={agents_with_scores[0]['agent_id']}, domain='{agents_with_scores[0]['domain']}', score={agents_with_scores[0]['quality_score']}")

        result = {
            "ranked_agents": agents_with_scores,
            "best_agent": agents_with_scores[0] if agents_with_scores else None
        }

        # Send progress update with discovered agents (extract task_id from context if available)
        # Note: We don't have task_id here, but the update_progress call will be made by the negotiator_agent caller
        return result

    except Exception as e:
        logger.error(f"[compare_agent_scores] Error in compare_agent_scores: {e}", exc_info=True)
        return {
            "ranked_agents": [],
            "best_agent": None
        }


def calculate_quality_score(reputation_data: Dict[str, Any], validation_data: Dict[str, Any]) -> float:
    """
    Calculate quality score (0-100) based on reputation and validation.

    Scoring:
    - Reputation (50 points):
      * Net reputation: -10 to +10 mapped to 0-30 points
      * Total votes: capped at 20 for 20 points
    - Validation (50 points):
      * Average score: 0-100 mapped to 0-35 points
      * Validation count: capped at 10 for 15 points
    """
    # Reputation scoring (max 50 points)
    reputation_score = reputation_data.get("reputationScore", 0)
    up_votes = reputation_data.get("upVotes", 0)
    down_votes = reputation_data.get("downVotes", 0)

    # Net reputation: -10 to +10 -> 0 to 30 points
    reputation_points = min(30, max(0, (reputation_score + 10) * 1.5))

    # Vote participation: cap at 20 votes for max 20 points
    total_votes = up_votes + down_votes
    participation_points = min(20, total_votes)

    reputation_total = reputation_points + participation_points

    # Validation scoring (max 50 points)
    validation_count = validation_data.get("validationCount", 0)
    average_score = validation_data.get("averageScore", 0)

    # Average score: 0-100 -> 0-35 points
    score_points = (average_score / 100) * 35

    # Validation count: cap at 10 validations for max 15 points
    count_points = min(15, validation_count * 1.5)

    validation_total = score_points + count_points

    # Total quality score
    return round(reputation_total + validation_total, 2)
