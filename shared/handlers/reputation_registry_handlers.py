from web3 import Web3
import json

# -------- CONFIG --------
RPC_URL = "https://testnet.hashio.io/api"  # or your RPC endpoint


PRIVATE_KEY = "0x2ab3764213f6057077fa8b9a80fb4d9e06074ab034284c1a41bb3ec8c920c31d"
CONTRACT_ADDRESS = "0xF7Ef87cE514550ED6311a7B3DAE552E67e33e34E"
IDENTITY_REGISTRY_ADDRESS = "0x1194bDf550b41C9bF2BB5E86009D1617ae6B4279"

# -------- SETUP --------
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Load ABI
with open("../contracts/ReputationRegistry.sol/ReputationRegistry.json") as f:
    contract_json = json.load(f)
    abi = contract_json["abi"]

reputation_registry = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)

# -------- WRITE FUNCTION EXAMPLE --------
def accept_feedback(agent_client_id: int, agent_server_id: int):
    tx = reputation_registry.functions.acceptFeedback(agent_client_id, agent_server_id).build_transaction({
        "from": wallet_address,
        "nonce": web3.eth.get_transaction_count(wallet_address),
        "gas": 200000,
        "gasPrice": web3.eth.gas_price,
    })

    signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
    tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

    print("⏳ Waiting for confirmation:", tx_hash.hex())
    receipt = web3.eth.wait_for_transaction_receipt(tx_hash)
    print("✅ Feedback accepted! Receipt:")
    print(receipt)


# -------- READ FUNCTION EXAMPLES --------
def is_feedback_authorized(agent_client_id: int, agent_server_id: int):
    authorized, feedback_auth_id = reputation_registry.functions.isFeedbackAuthorized(agent_client_id, agent_server_id).call()
    return {"authorized": authorized, "feedback_auth_id": feedback_auth_id.hex()}


def get_feedback_auth_id(agent_client_id: int, agent_server_id: int):
    feedback_auth_id = reputation_registry.functions.getFeedbackAuthId(agent_client_id, agent_server_id).call()
    return feedback_auth_id.hex()


# Example usage:
# accept_feedback(1, 2)
# print(is_feedback_authorized(1, 2))
# print(get_feedback_auth_id(1, 2))
