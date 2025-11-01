from __future__ import annotations

import json
import logging
import os
from pathlib import Path
from typing import Any

try:
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# -------- CONFIG --------
RPC_URL = os.getenv("IDENTITY_REGISTRY_RPC_URL", "https://testnet.hashio.io/api")
PRIVATE_KEY = os.getenv("IDENTITY_REGISTRY_PRIVATE_KEY", "")
IDENTITY_CONTRACT_ADDRESS = os.getenv(
    "IDENTITY_CONTRACT_ADDRESS",
    "0x1194bDf550b41C9bF2BB5E86009D1617ae6B4279",
)

IDENTITY_REGISTRY = None
wallet_address = ""
web3 = None

if Web3 is not None and PRIVATE_KEY:
    try:
        web3 = Web3(Web3.HTTPProvider(RPC_URL))
        account = web3.eth.account.from_key(PRIVATE_KEY)
        wallet_address = account.address

        artifact_path = (
            Path(__file__).resolve().parents[1]
            / "contracts"
            / "IdentityRegistry.sol"
            / "IdentityRegistry.json"
        )
        if artifact_path.exists():
            with artifact_path.open("r", encoding="utf-8") as f:
                contract_json = json.load(f)
                abi = contract_json["abi"]
            IDENTITY_REGISTRY = web3.eth.contract(
                address=IDENTITY_CONTRACT_ADDRESS,
                abi=abi,
            )
        else:
            logger.warning(
                "Identity registry ABI not found at %s. Registry functions are disabled.",
                artifact_path,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise identity registry handler: %s", exc)
else:
    if Web3 is None:
        logger.info(
            "web3.py is not installed; identity registry handlers operating in stub mode."
        )
    else:
        logger.info(
            "IDENTITY_REGISTRY_PRIVATE_KEY not configured; identity registry handlers disabled."
        )


def _ensure_registry() -> None:
    if IDENTITY_REGISTRY is None:
        raise RuntimeError(
            "Identity registry is unavailable in this environment. "
            "Ensure web3.py is installed and the contract ABI is present."
        )


# -------- WRITE FUNCTIONS --------
def register_agent(domain: str, agent_address: str = None):
    _ensure_registry()
    if agent_address is None:
        agent_address = wallet_address

    tx = IDENTITY_REGISTRY.functions.newAgent(domain, agent_address).build_transaction({
        "from": wallet_address,
        "value": web3.to_wei(0.005, "ether"),
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Agent Registered! Receipt:", receipt)
    return receipt


def update_agent(agent_id: int, new_domain: str = "", new_address: str = ""):
    _ensure_registry()

    tx = IDENTITY_REGISTRY.functions.updateAgent(agent_id, new_domain, new_address).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })
    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)
    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Agent Updated! Receipt:", receipt)
    return receipt


# -------- READ FUNCTIONS --------
def get_agent(agent_id: int):
    _ensure_registry()
    try:
        agent = IDENTITY_REGISTRY.functions.getAgent(agent_id).call()
        return agent
    except Exception as e:
        print("❌ Error:", e)
        return None


def resolve_by_domain(domain: str):
    _ensure_registry()
    try:
        agent = IDENTITY_REGISTRY.functions.resolveByDomain(domain).call()
        return agent
    except Exception as e:
        print("❌ Error:", e)
        return None


def resolve_by_address(address: str):
    _ensure_registry()
    try:
        agent = IDENTITY_REGISTRY.functions.resolveByAddress(address).call()
        return agent
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_agent_count():
    _ensure_registry()
    return IDENTITY_REGISTRY.functions.getAgentCount().call()


def agent_exists(agent_id: int):
    _ensure_registry()
    return IDENTITY_REGISTRY.functions.agentExists(agent_id).call()


# -------- ERC8004 EXTENDED FUNCTIONS --------
def get_agent_reputation(agent_id: int):
    """
    Get an agent's reputation score.
    Returns 0 if ReputationRegistry is not set.
    """
    _ensure_registry()
    try:
        score = IDENTITY_REGISTRY.functions.getAgentReputation(agent_id).call()
        return score
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_agent_vote_counts(agent_id: int):
    """
    Get vote counts for an agent.
    Returns (upVotes, downVotes).
    Returns (0, 0) if ReputationRegistry is not set.
    """
    _ensure_registry()
    try:
        up_votes, down_votes = IDENTITY_REGISTRY.functions.getAgentVoteCounts(agent_id).call()
        return {"upVotes": up_votes, "downVotes": down_votes}
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_agent_validation(agent_id: int):
    """
    Get validation data for an agent.
    Returns (validationCount, averageScore).
    Returns (0, 0) if ValidationRegistry is not set.
    """
    _ensure_registry()
    try:
        validation_count, average_score = IDENTITY_REGISTRY.functions.getAgentValidation(agent_id).call()
        return {"validationCount": validation_count, "averageScore": average_score}
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_agent_full_info(agent_id: int):
    """
    Get comprehensive agent information including identity, reputation, and validation.
    Returns:
        - agentInfo: The agent's identity information (agentId, agentDomain, agentAddress)
        - reputationScore: The agent's reputation score
        - upVotes: Number of up votes
        - downVotes: Number of down votes
        - validationCount: Number of validations received
        - validationScore: Average validation score (0-100)
    """
    _ensure_registry()
    try:
        result = IDENTITY_REGISTRY.functions.getAgentFullInfo(agent_id).call()
        agent_info, reputation_score, up_votes, down_votes, validation_count, validation_score = result

        return {
            "agentInfo": {
                "agentId": agent_info[0],
                "agentDomain": agent_info[1],
                "agentAddress": agent_info[2]
            },
            "reputationScore": reputation_score,
            "upVotes": up_votes,
            "downVotes": down_votes,
            "validationCount": validation_count,
            "validationScore": validation_score
        }
    except Exception as e:
        print("❌ Error:", e)
        return None


# -------- DOMAIN LISTING FUNCTIONS --------
def get_all_domains():
    """
    Get all registered domain names.
    Returns a list of all domains registered in the identity registry.
    """
    _ensure_registry()
    try:
        domains = IDENTITY_REGISTRY.functions.getAllDomains().call()
        return domains
    except Exception as e:
        print("❌ Error:", e)
        return []


def get_domains_paginated(offset: int = 0, limit: int = 100):
    """
    Get paginated list of registered domains.

    Args:
        offset: Starting index (default: 0)
        limit: Maximum number of domains to return (default: 100)

    Returns:
        Dictionary with:
        - domains: List of domain names
        - total: Total number of registered domains
    """
    _ensure_registry()
    try:
        domains, total = IDENTITY_REGISTRY.functions.getDomainsPaginated(offset, limit).call()
        return {
            "domains": domains,
            "total": total,
            "offset": offset,
            "limit": limit
        }
    except Exception as e:
        print("❌ Error:", e)
        return {
            "domains": [],
            "total": 0,
            "offset": offset,
            "limit": limit
        }
