from web3 import Web3
import json

# -------- CONFIG --------
RPC_URL = "https://testnet.hashio.io/api"

PRIVATE_KEY = "0x2ab3764213f6057077fa8b9a80fb4d9e06074ab034284c1a41bb3ec8c920c31d"
VALIDATION_CONTRACT_ADDRESS = "0x0362243248B2C6f94c62da42d29F141570d6a281"

# -------- SETUP --------
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Load ABI
with open("../contracts/ValidationRegistry.sol/ValidationRegistry.json") as f:
    contract_json = json.load(f)
    abi = contract_json["abi"]

validation_registry = web3.eth.contract(address=VALIDATION_CONTRACT_ADDRESS, abi=abi)


# -------- WRITE FUNCTIONS --------
def submit_validation(agent_id: int, score: int, data_uri: str = ""):
    """
    Submit a validation for an agent with a score (0-100).
    Requires that the agent exists and the validator hasn't validated before.

    Args:
        agent_id: The ID of the agent being validated
        score: Validation score (0-100)
        data_uri: Optional URI pointing to validation data/evidence
    """
    if score < 0 or score > 100:
        print("❌ Error: Score must be between 0 and 100")
        return None

    tx = validation_registry.functions.submitValidation(agent_id, score, data_uri).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Validation Submitted! Receipt:", receipt)
    return receipt


# -------- READ FUNCTIONS --------
def get_validation(agent_id: int):
    """
    Get validation data for an agent.
    Returns a dictionary with validationCount and averageScore.
    """
    try:
        validation_count, average_score = validation_registry.functions.getValidation(agent_id).call()
        return {
            "validationCount": validation_count,
            "averageScore": average_score
        }
    except Exception as e:
        print("❌ Error:", e)
        return None


def has_validated(agent_id: int, validator_address: str = None):
    """
    Check if a specific address has already validated an agent.
    If validator_address is not provided, uses the wallet_address.
    """
    if validator_address is None:
        validator_address = wallet_address

    try:
        validated = validation_registry.functions.hasValidated(agent_id, validator_address).call()
        return validated
    except Exception as e:
        print("❌ Error:", e)
        return None


def get_full_validation_info(agent_id: int):
    """
    Get comprehensive validation information for an agent.
    Returns validation count, average score, and whether the current wallet has validated.
    """
    try:
        validation_count, average_score = validation_registry.functions.getValidation(agent_id).call()
        validated = validation_registry.functions.hasValidated(agent_id, wallet_address).call()

        return {
            "agentId": agent_id,
            "validationCount": validation_count,
            "averageScore": average_score,
            "hasValidated": validated
        }
    except Exception as e:
        print("❌ Error:", e)
        return None
