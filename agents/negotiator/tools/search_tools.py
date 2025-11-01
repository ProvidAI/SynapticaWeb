"""Simplified agent search tools using Identity, Reputation, and Validation registries."""

import sys
import os
from typing import List, Dict, Any

from strands import tool

# Add shared to path for imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "../../../"))

from shared.handlers.identity_registry_handlers import (
    get_agent,
    get_agent_count,
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
async def find_agents(domain: str) -> List[Dict[str, Any]]:
    """
    Search for agents by domain keyword in the Identity Registry.

    This tool retrieves all registered domains and uses AI to determine which ones
    are relevant to the search query. Only relevant domains are resolved.

    Args:
        domain: Domain keyword or description to search for (e.g., "trading", "oracle", "data analysis")

    Returns:
        List of matching agents with basic info:
        [
            {
                "agent_id": int,
                "domain": str,
                "address": str
            },
            ...
        ]

    Example:
        agents = await find_agents("trading bots for cryptocurrency")
        # AI will identify relevant domains like "crypto-trading-bot", "trading-analytics", etc.
    """
    try:
        # Get all registered domains from the contract
        all_domains = get_all_domains()

        if not all_domains:
            return []

        # Return all domains for AI to filter
        # The AI agent will receive this list and determine which are relevant
        # Then it will call resolve_by_domain for each relevant one
        return {
            "all_domains": all_domains,
            "search_query": domain,
            "instruction": "Use AI to identify which domains are relevant to the search query, then resolve each relevant domain using resolve_by_domain."
        }

    except Exception as e:
        print(f"Error in find_agents: {e}")
        return []


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
            "address": str
        }

    Example:
        # After AI determines "crypto-trading-bot" is relevant
        agent = await resolve_agent_by_domain("crypto-trading-bot")
    """
    try:
        agent_data = resolve_by_domain(domain)
        if agent_data:
            return {
                "agent_id": agent_data[0],
                "domain": agent_data[1],
                "address": agent_data[2]
            }
        return None
    except Exception as e:
        print(f"Error resolving domain {domain}: {e}")
        return None


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
        agents_with_scores = []

        for agent_id in agent_ids:
            try:
                # Get agent identity
                agent_data = get_agent(agent_id)
                if not agent_data:
                    continue

                # Get reputation data
                rep_info = get_full_reputation_info(agent_id)
                if not rep_info:
                    rep_info = {"reputationScore": 0, "upVotes": 0, "downVotes": 0}

                # Get validation data
                val_info = get_full_validation_info(agent_id)
                if not val_info:
                    val_info = {"validationCount": 0, "averageScore": 0}

                # Calculate quality score
                quality_score = calculate_quality_score(rep_info, val_info)

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
                print(f"Error processing agent {agent_id}: {e}")
                continue

        # Sort by quality score (descending)
        agents_with_scores.sort(key=lambda x: x["quality_score"], reverse=True)

        # Add ranks
        for idx, agent in enumerate(agents_with_scores, 1):
            agent["rank"] = idx

        return {
            "ranked_agents": agents_with_scores,
            "best_agent": agents_with_scores[0] if agents_with_scores else None
        }

    except Exception as e:
        print(f"Error in compare_agent_scores: {e}")
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
