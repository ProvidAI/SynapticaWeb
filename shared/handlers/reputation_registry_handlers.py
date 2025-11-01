from __future__ import annotations

import json
import logging
import os
from pathlib import Path

try:
    from web3 import Web3
except ModuleNotFoundError:  # pragma: no cover
    Web3 = None  # type: ignore[assignment]

logger = logging.getLogger(__name__)

# -------- CONFIG --------
RPC_URL = os.getenv("REPUTATION_REGISTRY_RPC_URL", "https://testnet.hashio.io/api")
PRIVATE_KEY = os.getenv("REPUTATION_REGISTRY_PRIVATE_KEY", "")
REPUTATION_CONTRACT_ADDRESS = os.getenv(
    "REPUTATION_CONTRACT_ADDRESS",
    "0xF7Ef87cE514550ED6311a7B3DAE552E67e33e34E",
)

reputation_registry = None
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
            / "ReputationRegistry.sol"
            / "ReputationRegistry.json"
        )
        if artifact_path.exists():
            with artifact_path.open("r", encoding="utf-8") as f:
                contract_json = json.load(f)
                abi = contract_json["abi"]
            reputation_registry = web3.eth.contract(
                address=REPUTATION_CONTRACT_ADDRESS,
                abi=abi,
            )
        else:
            logger.warning(
                "Reputation registry ABI not found at %s; handler disabled.",
                artifact_path,
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to initialise reputation registry handler: %s", exc)
else:
    if Web3 is None:
        logger.info(
            "web3.py not installed; reputation registry handlers operating in stub mode."
        )
    else:
        logger.info(
            "REPUTATION_REGISTRY_PRIVATE_KEY not configured; reputation registry handlers disabled."
        )


def _ensure_registry() -> None:
    if reputation_registry is None:
        raise RuntimeError(
            "Reputation registry unavailable. Install web3.py and provide contract configuration."
        )


# -------- WRITE FUNCTIONS --------
def vote_up(agent_id: int):
    """
    Vote up an agent to increase their reputation score.
    Requires that the agent exists and the voter hasn't voted before.
    """
    _ensure_registry()
    tx = reputation_registry.functions.voteUp(agent_id).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Vote Up Recorded! Receipt:", receipt)
    return receipt


def vote_down(agent_id: int):
    """
    Vote down an agent to decrease their reputation score.
    Requires that the agent exists and the voter hasn't voted before.
    """
    _ensure_registry()
    tx = reputation_registry.functions.voteDown(agent_id).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Vote Down Recorded! Receipt:", receipt)
    return receipt


# -------- READ FUNCTIONS --------
def get_reputation(agent_id: int):
    """
    Get an agent's reputation score.
    Returns the net reputation (upvotes - downvotes).
    """
    _ensure_registry()
    try:
        score = reputation_registry.functions.getReputation(agent_id).call()
        return score
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_vote_counts(agent_id: int):
    """
    Get vote counts for an agent.
    Returns a dictionary with upVotes and downVotes.
    """
    _ensure_registry()
    try:
        up_votes, down_votes = reputation_registry.functions.getVoteCounts(agent_id).call()
        return {"upVotes": up_votes, "downVotes": down_votes}
    except Exception as e:
        print("❌ Error:", e)
        return None


def has_voted(agent_id: int, voter_address: str = None):
    """
    Check if a specific address has already voted for an agent.
    If voter_address is not provided, uses the wallet_address.
    """
    _ensure_registry()
    if voter_address is None:
        voter_address = wallet_address

    try:
        voted = reputation_registry.functions.hasVoted(agent_id, voter_address).call()
        return voted
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_full_reputation_info(agent_id: int):
    """
    Get comprehensive reputation information for an agent.
    Returns score, vote counts, and whether the current wallet has voted.
    """
    _ensure_registry()
    try:
        score = reputation_registry.functions.getReputation(agent_id).call()
        up_votes, down_votes = reputation_registry.functions.getVoteCounts(agent_id).call()
        voted = reputation_registry.functions.hasVoted(agent_id, wallet_address).call()

        return {
            "agentId": agent_id,
            "reputationScore": score,
            "upVotes": up_votes,
            "downVotes": down_votes,
            "hasVoted": voted
        }
    except Exception as e:
        print("❌ Error:", e)
        return None
