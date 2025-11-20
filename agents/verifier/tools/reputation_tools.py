"""
Reputation Management Tools for Verifier Agent

This module provides functions for updating agent reputation scores after verification.
Updates are applied to BOTH the database (local performance tracking) and blockchain
(public reputation on Hedera via ReputationRegistry smart contract).

Key Features:
- Dual updates: Database + Blockchain (always)
- Automatic payment multiplier adjustment
- Comprehensive audit trail and logging
- Graceful degradation (database commits even if blockchain fails)
- Transaction receipts for verification

Usage:
    from agents.verifier.tools.reputation_tools import (
        increase_agent_reputation,
        decrease_agent_reputation
    )

    # After successful verification
    result = await increase_agent_reputation(
        agent_id="literature-miner-001",
        quality_score=0.85,
        task_id="task_123",
        verification_result={...}
    )

    # After failed verification
    result = await decrease_agent_reputation(
        agent_id="literature-miner-001",
        quality_score=0.30,
        task_id="task_123",
        verification_result={...},
        failure_reason="Insufficient citations"
    )
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Any, Dict, Optional

from shared.database import SessionLocal, AgentReputation, Agent
from shared.handlers import reputation_registry_handlers, identity_registry_handlers

logger = logging.getLogger(__name__)

# ============================================================================
# CONSTANTS AND CONFIGURATION
# ============================================================================

# Reputation score formula weights
QUALITY_WEIGHT = 0.7  # 70% weight on average quality
SUCCESS_WEIGHT = 0.3  # 30% weight on success rate

# Payment multiplier tiers
TIER_EXCELLENT = 0.8  # ≥ 0.8 reputation → 1.2x payment (20% bonus)
TIER_GOOD = 0.6       # ≥ 0.6 reputation → 1.0x payment (standard)
TIER_FAIR = 0.4       # ≥ 0.4 reputation → 0.9x payment (10% penalty)
# < 0.4 reputation → 0.8x payment (20% penalty)

MULTIPLIER_EXCELLENT = 1.2
MULTIPLIER_GOOD = 1.0
MULTIPLIER_FAIR = 0.9
MULTIPLIER_POOR = 0.8


# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def _calculate_payment_multiplier(reputation_score: float) -> float:
    """
    Calculate payment multiplier based on reputation score.

    Tiers:
    - ≥ 0.8: 1.2x (excellent - 20% bonus)
    - 0.6-0.79: 1.0x (good - standard rate)
    - 0.4-0.59: 0.9x (fair - 10% penalty)
    - < 0.4: 0.8x (poor - 20% penalty)

    Args:
        reputation_score: Float between 0 and 1

    Returns:
        Payment multiplier (0.8 to 1.2)
    """
    if reputation_score >= TIER_EXCELLENT:
        return MULTIPLIER_EXCELLENT
    elif reputation_score >= TIER_GOOD:
        return MULTIPLIER_GOOD
    elif reputation_score >= TIER_FAIR:
        return MULTIPLIER_FAIR
    else:
        return MULTIPLIER_POOR


def _calculate_reputation_score(
    avg_quality_score: float,
    success_rate: float
) -> float:
    """
    Calculate overall reputation score from quality and success metrics.

    Formula: reputation = 0.7 × avg_quality + 0.3 × success_rate

    This weights quality more heavily than success rate, which is appropriate
    for research tasks where quality matters more than volume.

    Args:
        avg_quality_score: Average quality score (0-1)
        success_rate: Success rate (0-1)

    Returns:
        Reputation score (0-1)
    """
    reputation = QUALITY_WEIGHT * avg_quality_score + SUCCESS_WEIGHT * success_rate
    return round(reputation, 4)


def _get_or_create_reputation(db, agent_id: str) -> AgentReputation:
    """
    Get existing reputation record or create new one.

    Args:
        db: Database session
        agent_id: Agent identifier

    Returns:
        AgentReputation record
    """
    reputation = db.query(AgentReputation).filter(
        AgentReputation.agent_id == agent_id
    ).first()

    if not reputation:
        logger.info(f"Creating new reputation record for agent: {agent_id}")
        reputation = AgentReputation(
            agent_id=agent_id,
            total_tasks=0,
            successful_tasks=0,
            failed_tasks=0,
            average_quality_score=0.0,
            reputation_score=0.5,  # Start at neutral
            payment_multiplier=1.0,
            last_updated=datetime.now(),
            meta={}
        )
        db.add(reputation)

    return reputation


def _update_meta_field(
    reputation: AgentReputation,
    task_id: str,
    quality_score: float,
    verification_result: Dict[str, Any],
    success: bool,
    blockchain_tx: Optional[str] = None,
    failure_reason: Optional[str] = None
) -> None:
    """
    Update meta field with verification details for audit trail.

    Args:
        reputation: AgentReputation record
        task_id: Task identifier
        quality_score: Quality score from verification
        verification_result: Full verification result dict
        success: Whether task succeeded
        blockchain_tx: Blockchain transaction hash (if any)
        failure_reason: Reason for failure (if applicable)
    """
    if reputation.meta is None:
        reputation.meta = {}

    if "recent_tasks" not in reputation.meta:
        reputation.meta["recent_tasks"] = []

    # Add task to recent history (keep last 10)
    task_record = {
        "task_id": task_id,
        "timestamp": datetime.now().isoformat(),
        "quality_score": quality_score,
        "success": success,
        "blockchain_tx": blockchain_tx,
    }

    if failure_reason:
        task_record["failure_reason"] = failure_reason

    # Store dimension scores if available
    if "dimension_scores" in verification_result:
        task_record["dimension_scores"] = verification_result["dimension_scores"]

    reputation.meta["recent_tasks"].append(task_record)

    # Keep only last 10 tasks
    if len(reputation.meta["recent_tasks"]) > 10:
        reputation.meta["recent_tasks"] = reputation.meta["recent_tasks"][-10:]


def _get_blockchain_agent_id(agent_id: str) -> Optional[int]:
    """
    Convert string agent_id/domain to numeric blockchain agent ID.

    The system has a dual identity system:
    - Database uses string domains as primary key (e.g., "literature-miner-001")
    - Blockchain uses auto-incremented numeric IDs (1, 2, 3...)

    This function resolves the string to the numeric ID required by blockchain.

    Resolution strategy:
    1. Check database meta field first (fast, cached)
    2. Fallback to blockchain query via resolveByDomain() (slower but authoritative)

    Args:
        agent_id: String agent identifier or domain name

    Returns:
        Numeric blockchain agent ID (uint256), or None if not found

    Example:
        >>> _get_blockchain_agent_id("literature-miner-001")
        1  # Numeric ID from blockchain
    """
    db = SessionLocal()
    try:
        # Strategy 1: Check database meta field (fast)
        agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
        if agent and agent.meta and "registry_agent_id" in agent.meta:
            numeric_id = int(agent.meta["registry_agent_id"])
            logger.debug(
                f"[_get_blockchain_agent_id] Found in database: "
                f"{agent_id} → {numeric_id}"
            )
            return numeric_id

        # Strategy 2: Query blockchain directly (slower but authoritative)
        logger.info(
            f"[_get_blockchain_agent_id] Not in database, querying blockchain "
            f"for domain: {agent_id}"
        )

        agent_data = identity_registry_handlers.resolve_by_domain(agent_id)

        if agent_data and len(agent_data) > 0:
            numeric_id = int(agent_data[0])  # First element is numeric agent ID
            logger.info(
                f"[_get_blockchain_agent_id] Blockchain resolved: "
                f"{agent_id} → {numeric_id}"
            )
            return numeric_id

        # Not found
        logger.warning(
            f"[_get_blockchain_agent_id] Agent not found on blockchain: {agent_id}"
        )
        return None

    except Exception as e:
        logger.error(
            f"[_get_blockchain_agent_id] Error resolving {agent_id}: {e}",
            exc_info=True
        )
        return None

    finally:
        db.close()


# ============================================================================
# MAIN REPUTATION UPDATE FUNCTIONS
# ============================================================================

async def increase_agent_reputation(
    agent_id: str,
    quality_score: float,
    task_id: str,
    verification_result: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Increase agent reputation after successful verification.

    Updates BOTH database and blockchain:
    1. Database (AgentReputation table):
       - Increments total_tasks and successful_tasks
       - Updates average_quality_score (running average)
       - Calculates new reputation_score (70% quality + 30% success rate)
       - Adjusts payment_multiplier based on new reputation
       - Stores verification details in meta field

    2. Blockchain (ReputationRegistry smart contract):
       - Calls vote_up() to increase on-chain reputation
       - Sends transaction to Hedera network
       - Waits for confirmation

    Args:
        agent_id: Agent identifier (e.g., "literature-miner-001")
        quality_score: Quality score from verification (0-1 scale)
        task_id: Task ID that was verified
        verification_result: Full verification result dict with dimension scores

    Returns:
        Dict containing:
        - success: Whether update succeeded
        - agent_id: Agent identifier
        - previous_reputation: Old reputation score
        - new_reputation: New reputation score
        - previous_multiplier: Old payment multiplier
        - new_multiplier: New payment multiplier
        - total_tasks: Total tasks after update
        - successful_tasks: Successful tasks after update
        - average_quality: New average quality score
        - blockchain_tx: Transaction hash (if blockchain update succeeded)
        - blockchain_success: Whether blockchain update succeeded
        - error: Error message (if any)

    Raises:
        ValueError: If quality_score is not between 0 and 1
    """
    if not 0 <= quality_score <= 1:
        raise ValueError(f"quality_score must be between 0 and 1, got {quality_score}")

    db = SessionLocal()
    blockchain_tx = None
    blockchain_success = False

    try:
        # ===== DATABASE UPDATE =====
        logger.info(
            f"[increase_reputation] Updating reputation for {agent_id}, "
            f"quality_score={quality_score}, task_id={task_id}"
        )

        # Get or create reputation record
        reputation = _get_or_create_reputation(db, agent_id)

        # Store previous values
        previous_reputation = reputation.reputation_score
        previous_multiplier = reputation.payment_multiplier

        # Increment task counters
        reputation.total_tasks += 1
        reputation.successful_tasks += 1

        # Update average quality score (running average)
        if reputation.total_tasks == 1:
            reputation.average_quality_score = quality_score
        else:
            total_quality = (
                reputation.average_quality_score * (reputation.total_tasks - 1) +
                quality_score
            )
            reputation.average_quality_score = total_quality / reputation.total_tasks

        # Calculate new reputation score
        success_rate = reputation.successful_tasks / reputation.total_tasks
        reputation.reputation_score = _calculate_reputation_score(
            reputation.average_quality_score,
            success_rate
        )

        # Update payment multiplier
        reputation.payment_multiplier = _calculate_payment_multiplier(
            reputation.reputation_score
        )

        # Update timestamp
        reputation.last_updated = datetime.now()

        # Commit database changes first
        db.commit()

        logger.info(
            f"[increase_reputation] Database updated: {agent_id} "
            f"reputation {previous_reputation:.3f} → {reputation.reputation_score:.3f}, "
            f"multiplier {previous_multiplier:.2f}x → {reputation.payment_multiplier:.2f}x"
        )

        # ===== BLOCKCHAIN UPDATE =====
        try:
            # Convert string agent_id to numeric blockchain ID
            blockchain_agent_id = _get_blockchain_agent_id(agent_id)

            if blockchain_agent_id is None:
                logger.warning(
                    f"[increase_reputation] Agent {agent_id} not found on blockchain, "
                    f"skipping blockchain vote"
                )
                blockchain_success = False
            else:
                logger.info(
                    f"[increase_reputation] Voting up on blockchain for {agent_id} "
                    f"(blockchain ID: {blockchain_agent_id})"
                )

                # Call blockchain vote_up function with numeric ID
                blockchain_receipt = reputation_registry_handlers.vote_up(blockchain_agent_id)

                if blockchain_receipt and blockchain_receipt.get("status") == 1:
                    blockchain_tx = blockchain_receipt.get("transactionHash", "").hex()
                    blockchain_success = True
                    logger.info(
                        f"[increase_reputation] Blockchain vote successful: {blockchain_tx}"
                    )
                else:
                    logger.warning(
                        f"[increase_reputation] Blockchain vote failed or pending: {blockchain_receipt}"
                    )

        except Exception as blockchain_error:
            # Log blockchain error but don't fail the entire operation
            logger.error(
                f"[increase_reputation] Blockchain update failed for {agent_id}: {blockchain_error}",
                exc_info=True
            )
            blockchain_success = False

        # Update meta field with blockchain tx hash
        _update_meta_field(
            reputation,
            task_id,
            quality_score,
            verification_result,
            success=True,
            blockchain_tx=blockchain_tx
        )

        # Commit meta field update
        db.commit()

        # Return success result
        return {
            "success": True,
            "agent_id": agent_id,
            "previous_reputation": previous_reputation,
            "new_reputation": reputation.reputation_score,
            "previous_multiplier": previous_multiplier,
            "new_multiplier": reputation.payment_multiplier,
            "total_tasks": reputation.total_tasks,
            "successful_tasks": reputation.successful_tasks,
            "average_quality": reputation.average_quality_score,
            "blockchain_tx": blockchain_tx,
            "blockchain_success": blockchain_success,
        }

    except Exception as e:
        db.rollback()
        logger.error(
            f"[increase_reputation] Failed to update reputation for {agent_id}: {e}",
            exc_info=True
        )
        return {
            "success": False,
            "agent_id": agent_id,
            "error": str(e)
        }

    finally:
        db.close()


async def decrease_agent_reputation(
    agent_id: str,
    quality_score: float,
    task_id: str,
    verification_result: Dict[str, Any],
    failure_reason: str,
) -> Dict[str, Any]:
    """
    Decrease agent reputation after failed verification.

    Updates BOTH database and blockchain:
    1. Database (AgentReputation table):
       - Increments total_tasks and failed_tasks
       - Updates average_quality_score (running average with low score)
       - Recalculates reputation_score
       - Adjusts payment_multiplier (may reduce pay rate)
       - Stores failure details in meta field

    2. Blockchain (ReputationRegistry smart contract):
       - Calls vote_down() to decrease on-chain reputation
       - Sends transaction to Hedera network
       - Waits for confirmation

    Args:
        agent_id: Agent identifier (e.g., "literature-miner-001")
        quality_score: Low quality score that caused failure (0-1 scale)
        task_id: Task ID that failed
        verification_result: Full verification result dict
        failure_reason: Why verification failed (for audit trail)

    Returns:
        Dict containing:
        - success: Whether update succeeded
        - agent_id: Agent identifier
        - previous_reputation: Old reputation score
        - new_reputation: New reputation score
        - previous_multiplier: Old payment multiplier
        - new_multiplier: New payment multiplier
        - total_tasks: Total tasks after update
        - failed_tasks: Failed tasks after update
        - average_quality: New average quality score
        - blockchain_tx: Transaction hash (if blockchain update succeeded)
        - blockchain_success: Whether blockchain update succeeded
        - error: Error message (if any)

    Raises:
        ValueError: If quality_score is not between 0 and 1
    """
    if not 0 <= quality_score <= 1:
        raise ValueError(f"quality_score must be between 0 and 1, got {quality_score}")

    db = SessionLocal()
    blockchain_tx = None
    blockchain_success = False

    try:
        # ===== DATABASE UPDATE =====
        logger.info(
            f"[decrease_reputation] Updating reputation for {agent_id}, "
            f"quality_score={quality_score}, task_id={task_id}, "
            f"reason={failure_reason}"
        )

        # Get or create reputation record
        reputation = _get_or_create_reputation(db, agent_id)

        # Store previous values
        previous_reputation = reputation.reputation_score
        previous_multiplier = reputation.payment_multiplier

        # Increment task counters
        reputation.total_tasks += 1
        reputation.failed_tasks += 1

        # Update average quality score (running average including low score)
        if reputation.total_tasks == 1:
            reputation.average_quality_score = quality_score
        else:
            total_quality = (
                reputation.average_quality_score * (reputation.total_tasks - 1) +
                quality_score
            )
            reputation.average_quality_score = total_quality / reputation.total_tasks

        # Calculate new reputation score
        success_rate = reputation.successful_tasks / reputation.total_tasks
        reputation.reputation_score = _calculate_reputation_score(
            reputation.average_quality_score,
            success_rate
        )

        # Update payment multiplier (may be reduced)
        reputation.payment_multiplier = _calculate_payment_multiplier(
            reputation.reputation_score
        )

        # Update timestamp
        reputation.last_updated = datetime.now()

        # Commit database changes first
        db.commit()

        logger.info(
            f"[decrease_reputation] Database updated: {agent_id} "
            f"reputation {previous_reputation:.3f} → {reputation.reputation_score:.3f}, "
            f"multiplier {previous_multiplier:.2f}x → {reputation.payment_multiplier:.2f}x"
        )

        # ===== BLOCKCHAIN UPDATE =====
        try:
            # Convert string agent_id to numeric blockchain ID
            blockchain_agent_id = _get_blockchain_agent_id(agent_id)

            if blockchain_agent_id is None:
                logger.warning(
                    f"[decrease_reputation] Agent {agent_id} not found on blockchain, "
                    f"skipping blockchain vote"
                )
                blockchain_success = False
            else:
                logger.info(
                    f"[decrease_reputation] Voting down on blockchain for {agent_id} "
                    f"(blockchain ID: {blockchain_agent_id})"
                )

                # Call blockchain vote_down function with numeric ID
                blockchain_receipt = reputation_registry_handlers.vote_down(blockchain_agent_id)

                if blockchain_receipt and blockchain_receipt.get("status") == 1:
                    blockchain_tx = blockchain_receipt.get("transactionHash", "").hex()
                    blockchain_success = True
                    logger.info(
                        f"[decrease_reputation] Blockchain vote successful: {blockchain_tx}"
                    )
                else:
                    logger.warning(
                        f"[decrease_reputation] Blockchain vote failed or pending: {blockchain_receipt}"
                    )

        except Exception as blockchain_error:
            # Log blockchain error but don't fail the entire operation
            logger.error(
                f"[decrease_reputation] Blockchain update failed for {agent_id}: {blockchain_error}",
                exc_info=True
            )
            blockchain_success = False

        # Update meta field with failure details
        _update_meta_field(
            reputation,
            task_id,
            quality_score,
            verification_result,
            success=False,
            blockchain_tx=blockchain_tx,
            failure_reason=failure_reason
        )

        # Commit meta field update
        db.commit()

        # Return success result
        return {
            "success": True,
            "agent_id": agent_id,
            "previous_reputation": previous_reputation,
            "new_reputation": reputation.reputation_score,
            "previous_multiplier": previous_multiplier,
            "new_multiplier": reputation.payment_multiplier,
            "total_tasks": reputation.total_tasks,
            "failed_tasks": reputation.failed_tasks,
            "average_quality": reputation.average_quality_score,
            "failure_reason": failure_reason,
            "blockchain_tx": blockchain_tx,
            "blockchain_success": blockchain_success,
        }

    except Exception as e:
        db.rollback()
        logger.error(
            f"[decrease_reputation] Failed to update reputation for {agent_id}: {e}",
            exc_info=True
        )
        return {
            "success": False,
            "agent_id": agent_id,
            "error": str(e)
        }

    finally:
        db.close()
