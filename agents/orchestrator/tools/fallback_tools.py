"""Fallback agent selection tools for retrying with alternative agents."""

import logging
from typing import Dict, Any, List, Optional

from strands import tool
from shared.task_progress import update_progress

logger = logging.getLogger(__name__)


@tool
async def find_fallback_agent(
    task_id: str,
    todo_id: str,
    failed_agent_id: str,
    capability_requirements: str,
    budget_limit: Optional[float] = None,
    min_reputation_score: Optional[float] = 0.2,
) -> Dict[str, Any]:
    """
    Find a fallback agent after the primary agent has failed quality verification.

    This tool discovers alternative agents from the marketplace, filtering out
    the failed agent, and selects the next best option based on quality scores.

    Workflow:
    1. Call negotiator's find_agents() to discover agents matching capabilities
    2. Call negotiator's compare_agent_scores() to rank agents by quality
    3. Filter out the failed agent from ranked list
    4. Select next best agent (highest quality score among remaining)
    5. Create payment proposal for fallback agent

    Args:
        task_id: Task ID for progress tracking
        todo_id: TODO item ID
        failed_agent_id: ID/domain of agent that failed verification
        capability_requirements: Description of required agent capabilities
        budget_limit: Maximum budget for the task (optional)
        min_reputation_score: Minimum reputation score (0-1, default 0.2)

    Returns:
        Dict containing:
        - success: bool
        - fallback_agent: Agent details (id, domain, quality_score)
        - payment_id: Payment proposal ID for fallback agent
        - ranked_agents: List of all alternative agents considered
        - message: Status message
    """
    try:
        logger.info(f"[find_fallback_agent] Finding fallback agent for {todo_id}, failed: {failed_agent_id}")

        # Update progress
        update_progress(task_id, f"fallback_search_{todo_id}", "running", {
            "message": "Searching for backup agent...",
            "todo_id": todo_id,
            "failed_agent": failed_agent_id
        })

        # Import negotiator tools
        from agents.negotiator.tools.search_tools import find_agents, compare_agent_scores
        from agents.negotiator.tools.payment_tools import create_payment_request

        # Step 1: Find agents matching capability requirements
        logger.info(f"[find_fallback_agent] Searching for agents with capabilities: {capability_requirements}")

        # Extract domain keywords from capability requirements
        # For MVP, use the capability_requirements as domain search term
        domain_search_term = capability_requirements.split(",")[0].strip()  # Use first capability

        agents_result = await find_agents(domain=domain_search_term)

        if not agents_result.get("success") or not agents_result.get("agent_domains"):
            logger.error(f"[find_fallback_agent] No agents found for domain: {domain_search_term}")
            return {
                "success": False,
                "error": "No alternative agents found",
                "failed_agent": failed_agent_id
            }

        agent_domains = agents_result["agent_domains"]
        logger.info(f"[find_fallback_agent] Found {len(agent_domains)} potential agents: {agent_domains}")

        # Step 2: Resolve agent IDs and rank by quality scores
        # Extract agent IDs from domains
        agent_ids = []
        for domain in agent_domains:
            # Try to extract numeric ID from domain
            import re
            id_match = re.search(r'(\d+)', domain)
            if id_match:
                agent_ids.append(int(id_match.group(1)))

        if not agent_ids:
            logger.error(f"[find_fallback_agent] Could not extract agent IDs from domains: {agent_domains}")
            return {
                "success": False,
                "error": "Could not identify agent IDs",
                "failed_agent": failed_agent_id
            }

        logger.info(f"[find_fallback_agent] Comparing quality scores for agents: {agent_ids}")

        # Compare agent scores
        scores_result = await compare_agent_scores(
            agent_ids=agent_ids,
            task_id=task_id,
            task_name=f"Fallback selection for {todo_id}",
            todo_id=todo_id
        )

        if not scores_result.get("success") or not scores_result.get("ranked_agents"):
            logger.error(f"[find_fallback_agent] Failed to rank agents")
            return {
                "success": False,
                "error": "Agent ranking failed",
                "failed_agent": failed_agent_id
            }

        ranked_agents = scores_result["ranked_agents"]
        logger.info(f"[find_fallback_agent] Ranked {len(ranked_agents)} agents")

        # Step 3: Filter out failed agent and select next best
        fallback_candidates = []
        for agent in ranked_agents:
            agent_id_str = str(agent.get("agent_id", ""))
            agent_domain = agent.get("domain", "")

            # Skip if this is the failed agent
            if agent_id_str == failed_agent_id or agent_domain == failed_agent_id:
                logger.info(f"[find_fallback_agent] Skipping failed agent: {agent_domain}")
                continue

            # Check minimum reputation score
            quality_score = agent.get("quality_score", 0)
            if quality_score < min_reputation_score * 100:  # quality_score is 0-100
                logger.info(f"[find_fallback_agent] Skipping low-quality agent: {agent_domain} (score: {quality_score})")
                continue

            fallback_candidates.append(agent)

        # PHASE 3.1: Multi-tier fallback search with progressive quality relaxation
        if not fallback_candidates:
            logger.warning(f"[find_fallback_agent] No agents found at quality threshold {min_quality_threshold}%")

            # Tier 2: Relax quality threshold to 10%
            logger.info(f"[find_fallback_agent] Trying with relaxed quality threshold: 10%")
            fallback_candidates = []
            for agent in ranked_agents:
                agent_id = str(agent.get("agent_id"))
                quality_score = agent.get("quality_score", 0)

                if agent_id == failed_agent_id:
                    continue  # Skip failed agent

                if quality_score >= 10:  # Relaxed threshold
                    fallback_candidates.append(agent)

        if not fallback_candidates:
            # Tier 3: Accept ANY agent (quality >= 0)
            logger.warning(f"[find_fallback_agent] No agents found at 10%, trying ANY available agent")
            fallback_candidates = []
            for agent in ranked_agents:
                agent_id = str(agent.get("agent_id"))

                if agent_id == failed_agent_id:
                    continue  # Skip failed agent

                # Accept any agent except the failed one
                fallback_candidates.append(agent)

        if not fallback_candidates:
            logger.error(f"[find_fallback_agent] No suitable fallback agents found after all tiers")
            return {
                "success": False,
                "error": "No alternative agents available (only failed agent exists in registry)",
                "failed_agent": failed_agent_id,
                "ranked_agents": ranked_agents,
                "troubleshooting": [
                    "Register additional agents in the identity registry for fallback support",
                    "Current registry only contains 1 agent or all are the same as failed agent",
                    "Recommendation: Maintain at least 2-3 agents for redundancy"
                ]
            }

        # Select best fallback (first in ranked list after filtering)
        fallback_agent = fallback_candidates[0]
        quality_tier = "high" if fallback_agent.get("quality_score", 0) >= min_quality_threshold else \
                      "medium" if fallback_agent.get("quality_score", 0) >= 10 else "low"

        logger.info(f"[find_fallback_agent] Selected fallback agent: {fallback_agent.get('domain')} " +
                   f"(score: {fallback_agent.get('quality_score')}, tier: {quality_tier})")

        # Update progress with fallback agent selection
        update_progress(task_id, f"fallback_selected_{todo_id}", "completed", {
            "message": f"✓ Backup agent selected: {fallback_agent.get('domain')}",
            "todo_id": todo_id,
            "fallback_agent": fallback_agent,
            "quality_score": fallback_agent.get("quality_score"),
            "ranked_agents": fallback_candidates[:3]  # Show top 3
        })

        # Step 4: Create payment proposal for fallback agent
        logger.info(f"[find_fallback_agent] Creating payment proposal for fallback agent")

        payment_result = await create_payment_request(
            from_agent="orchestrator",
            to_agent_id=fallback_agent.get("agent_id"),
            to_agent_domain=fallback_agent.get("domain"),
            amount=budget_limit or 100.0,
            task_description=f"Fallback execution for: {capability_requirements}",
            task_id=task_id,
            verifiers=["verifier_agent"],  # Always include verifier
            approvals_required=1,
            marketplace_fees={"platform_fee": 0.05}  # 5% fee
        )

        if not payment_result.get("success"):
            logger.error(f"[find_fallback_agent] Failed to create payment proposal: {payment_result}")
            return {
                "success": False,
                "error": "Payment proposal creation failed",
                "fallback_agent": fallback_agent,
                "payment_error": payment_result.get("error")
            }

        payment_id = payment_result.get("payment_id")
        logger.info(f"[find_fallback_agent] Created payment proposal: {payment_id}")

        return {
            "success": True,
            "fallback_agent": {
                "agent_id": fallback_agent.get("agent_id"),
                "domain": fallback_agent.get("domain"),
                "quality_score": fallback_agent.get("quality_score"),
                "reputation_score": fallback_agent.get("reputation_score"),
                "validation_score": fallback_agent.get("validation_score"),
            },
            "payment_id": payment_id,
            "ranked_agents": fallback_candidates[:5],  # Return top 5 alternatives
            "failed_agent": failed_agent_id,
            "message": f"✓ Fallback agent selected: {fallback_agent.get('domain')} (quality: {fallback_agent.get('quality_score')}/100)"
        }

    except Exception as e:
        logger.error(f"[find_fallback_agent] Error finding fallback agent: {e}", exc_info=True)

        update_progress(task_id, f"fallback_search_{todo_id}", "failed", {
            "message": "Fallback agent search failed",
            "todo_id": todo_id,
            "error": str(e)
        })

        return {
            "success": False,
            "error": str(e),
            "failed_agent": failed_agent_id
        }
