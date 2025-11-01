from web3 import Web3
import json

# -------- CONFIG --------
RPC_URL = "https://testnet.hashio.io/api"  # or your RPC endpoint
PRIVATE_KEY = "0x2ab3764213f6057077fa8b9a80fb4d9e06074ab034284c1a41bb3ec8c920c31d"
CONTRACT_ADDRESS = "0x0362243248B2C6f94c62da42d29F141570d6a281"
IDENTITY_REGISTRY_ADDRESS = "0x1194bDf550b41C9bF2BB5E86009D1617ae6B4279"

# -------- SETUP --------
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Load ABI
with open("../contracts/ValidationRegistry.sol/ValidationRegistry.json") as f:
    contract_json = json.load(f)
    abi = contract_json["abi"]

validation_registry = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

# -------- WRITE FUNCTIONS --------
def validation_request(agent_validator_id: int, agent_server_id: int, data_hash: str):
    """
    Create a validation request.
    data_hash: 0x-prefixed string representing bytes32
    """
    tx = validation_registry.functions.validationRequest(
        agent_validator_id, agent_server_id, data_hash
    ).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Validation request submitted! Receipt:")
    print(receipt)


def validation_response(data_hash: str, response: int):
    """
    Submit a validation response.
    response: integer 0-100
    """
    tx = validation_registry.functions.validationResponse(data_hash, response).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Validation response submitted! Receipt:")
    print(receipt)

# -------- READ FUNCTIONS --------
def get_validation_request(data_hash: str):
    return validation_registry.functions.getValidationRequest(data_hash).call()

def is_validation_pending(data_hash: str):
    exists, pending = validation_registry.functions.isValidationPending(data_hash).call()
    return {"exists": exists, "pending": pending}

def get_validation_response(data_hash: str):
    has_response, response = validation_registry.functions.getValidationResponse(data_hash).call()
    return {"has_response": has_response, "response": response}

def get_expiration_slots():
    return validation_registry.functions.getExpirationSlots().call()
