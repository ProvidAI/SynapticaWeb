from web3 import Web3
import json

# -------- CONFIG --------
RPC_URL = "https://testnet.hashio.io/api"

PRIVATE_KEY = "0x2ab3764213f6057077fa8b9a80fb4d9e06074ab034284c1a41bb3ec8c920c31d"
IDENTITY_CONTRACT_ADDRESS = "0x1194bDf550b41C9bF2BB5E86009D1617ae6B4279"


# -------- SETUP --------
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Load ABI (make sure JSON artifact exists)
with open("../contracts/IdentityRegistry.sol/IdentityRegistry.json") as f:
    contract_json = json.load(f)
    abi = contract_json["abi"]

identity_registry = web3.eth.contract(address=IDENTITY_CONTRACT_ADDRESS, abi=abi)


# -------- WRITE FUNCTIONS --------
def register_agent(domain: str, agent_address: str = None):
    if agent_address is None:
        agent_address = wallet_address

    tx = identity_registry.functions.newAgent(domain, agent_address).build_transaction({
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
    tx = identity_registry.functions.updateAgent(agent_id, new_domain, new_address).build_transaction({
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
    try:
        agent = identity_registry.functions.getAgent(agent_id).call()
        return agent
    except Exception as e:
        print("❌ Error:", e)
        return None


def resolve_by_domain(domain: str):
    try:
        agent = identity_registry.functions.resolveByDomain(domain).call()
        return agent
    except Exception as e:
        print("❌ Error:", e)
        return None


def resolve_by_address(address: str):
    try:
        agent = identity_registry.functions.resolveByAddress(address).call()
        return agent
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_agent_count():
    return identity_registry.functions.getAgentCount().call()


def agent_exists(agent_id: int):
    return identity_registry.functions.agentExists(agent_id).call()


# -------- ERC8004 EXTENDED FUNCTIONS --------
def get_agent_reputation(agent_id: int):
    """
    Get an agent's reputation score.
    Returns 0 if ReputationRegistry is not set.
    """
    try:
        score = identity_registry.functions.getAgentReputation(agent_id).call()
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
    try:
        up_votes, down_votes = identity_registry.functions.getAgentVoteCounts(agent_id).call()
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
    try:
        validation_count, average_score = identity_registry.functions.getAgentValidation(agent_id).call()
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
    try:
        result = identity_registry.functions.getAgentFullInfo(agent_id).call()
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
    try:
        domains = identity_registry.functions.getAllDomains().call()
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
    try:
        domains, total = identity_registry.functions.getDomainsPaginated(offset, limit).call()
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
