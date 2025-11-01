from web3 import Web3
import json

# -------- CONFIG --------
RPC_URL = "https://testnet.hashio.io/api"

PRIVATE_KEY = "0x2ab3764213f6057077fa8b9a80fb4d9e06074ab034284c1a41bb3ec8c920c31d"
CONTRACT_ADDRESS = "0x1194bDf550b41C9bF2BB5E86009D1617ae6B4279"


# -------- SETUP --------
web3 = Web3(Web3.HTTPProvider(RPC_URL))
account = web3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address

# Load ABI (make sure JSON artifact exists)
with open("../contracts/IdentityRegistry.sol/IdentityRegistry.json") as f:
    contract_json = json.load(f)
    abi = contract_json["abi"]

identity_registry = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)


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
