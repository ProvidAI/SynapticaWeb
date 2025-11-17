#!/usr/bin/env python
"""
Register agents to the NEW IdentityRegistry contract with metadata URIs.

This script is for the updated contract that includes the metadataUri parameter.

IMPORTANT: This requires the NEW contract to be deployed with the 3-parameter
newAgent function: newAgent(domain, address, metadataUri)

Usage:
    # Test with one agent
    python scripts/register_agents_with_metadata.py test

    # List registered agents
    python scripts/register_agents_with_metadata.py list

    # Register all agents
    python scripts/register_agents_with_metadata.py register
"""

import os
import sys
import json
import hashlib
from pathlib import Path
from dotenv import load_dotenv
from web3 import Web3
from eth_account import Account
from hiero_sdk_python import (
    Client as HederaClient,
    Network as HederaNetwork,
    AccountId as HederaAccountId,
    PrivateKey as HederaPrivateKey,
    EthereumTransaction,
    Hbar,
)
from hiero_sdk_python.response_code import ResponseCode

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from shared.database import SessionLocal, Agent as AgentModel

# Load environment variables
load_dotenv(override=True)

# -------- CONFIG --------
RPC_URL = os.getenv("HEDERA_RPC_URL", "https://testnet.hashio.io/api")
PRIVATE_KEY = os.getenv("HEDERA_PRIVATE_KEY")
HEDERA_ACCOUNT_ID = os.getenv("HEDERA_ACCOUNT_ID")
HEDERA_NETWORK = os.getenv("HEDERA_NETWORK", "testnet")
MAX_GAS_ALLOWANCE_HBAR = float(os.getenv("AGENT_METADATA_MAX_GAS_HBAR", "5.0"))
PRIORITY_FEE_GWEI = float(os.getenv("AGENT_METADATA_PRIORITY_FEE_GWEI", "2.0"))
CONTRACT_ADDRESS = os.getenv("IDENTITY_REGISTRY_ADDRESS") or os.getenv("IDENTITY_CONTRACT_ADDRESS")

# Metadata URL base (update this based on your hosting)
# Options:
#   - Local testing: "http://localhost:8001"
#   - IPFS: "https://ipfs.io/ipfs/YOUR_CID"
#   - Cloud storage: "https://your-bucket.s3.amazonaws.com/metadata"
#   - Your API: "https://api.providai.io/metadata"
#   - Local file (for testing): "file:///path/to/agent_metadata"
METADATA_BASE_URL = os.getenv("METADATA_BASE_URL", "https://providai.io/metadata")

# -------- VALIDATION --------
if not PRIVATE_KEY or PRIVATE_KEY == "your_hedera_private_key_here":
    print("❌ Error: HEDERA_PRIVATE_KEY not set in .env file")
    sys.exit(1)

if not HEDERA_ACCOUNT_ID:
    print("❌ Error: HEDERA_ACCOUNT_ID not set in .env file")
    sys.exit(1)

if not CONTRACT_ADDRESS:
    print("❌ Error: IDENTITY_REGISTRY_ADDRESS not set in .env file")
    print("\nYou need to deploy the NEW IdentityRegistry contract first")
    print("Run: python scripts/deploy_identity_registry.py")
    sys.exit(1)

# -------- WEB3 SETUP --------
print("🔧 Connecting to Hedera testnet...")
web3 = Web3(Web3.HTTPProvider(RPC_URL))

if not web3.is_connected():
    print("❌ Failed to connect to Hedera")
    sys.exit(1)

print(f"✅ Connected to Hedera testnet")

# Setup account
account = web3.eth.account.from_key(PRIVATE_KEY)
wallet_address = account.address
print(f"📍 Wallet address: {wallet_address}")

balance = web3.eth.get_balance(wallet_address)
balance_hbar = web3.from_wei(balance, 'ether')
print(f"💰 Balance: {balance_hbar} HBAR")

def _load_hedera_private_key(value: str) -> HederaPrivateKey:
    raw = value.strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) == 64:
        return HederaPrivateKey.from_bytes_ecdsa(bytes.fromhex(raw))
    return HederaPrivateKey.from_string(raw)


hedera_network_name = HEDERA_NETWORK if HEDERA_NETWORK in {"mainnet", "testnet", "previewnet"} else "testnet"
hedera_client = HederaClient(HederaNetwork(hedera_network_name))
hedera_client.set_operator(
    HederaAccountId.from_string(HEDERA_ACCOUNT_ID),
    _load_hedera_private_key(PRIVATE_KEY),
)

# Load contract ABI
contract_json_path = Path(__file__).parent.parent / "shared/contracts/IdentityRegistry.sol/IdentityRegistry.json"

if not contract_json_path.exists():
    print(f"\n❌ Contract JSON not found at: {contract_json_path}")
    print("\nThe contract needs to be compiled with the NEW IdentityRegistry.sol")
    print("Make sure you have the version with metadataUri parameter")
    sys.exit(1)

with open(contract_json_path) as f:
    contract_data = json.load(f)
    abi = contract_data['abi']

# Create contract instance
print(f"\n🔧 Loading Identity Registry contract...")
identity_registry = web3.eth.contract(address=CONTRACT_ADDRESS, abi=abi)
print(f"✅ Contract loaded at: {CONTRACT_ADDRESS}")

# Verify contract has the new newAgent function with 3 parameters
try:
    new_agent_function = identity_registry.functions.newAgent
    # This will help us check if the function signature is correct
    print("✅ Contract has newAgent function")
except AttributeError:
    print("❌ Contract doesn't have newAgent function!")
    sys.exit(1)


# -------- HELPER FUNCTIONS --------

_NONCE_CACHE: dict[str, int] = {}


def _get_next_nonce(address: str) -> int:
    try:
        network_nonce = web3.eth.get_transaction_count(address)
    except Exception:
        network_nonce = 0
    cached = _NONCE_CACHE.get(address)
    next_nonce = network_nonce if cached is None else max(network_nonce, cached)
    _NONCE_CACHE[address] = next_nonce + 1
    return next_nonce


def _derive_agent_account(domain: str):
    """Derive the deterministic agent wallet from its domain."""
    seed = hashlib.sha256(domain.encode()).hexdigest()
    return Account.from_key("0x" + seed)


def _ensure_agent_balance(agent_address: str) -> bool:
    """Fund agent wallet with a small amount of HBAR if needed."""
    min_balance = web3.to_wei(0.002, "ether")

    try:
        current_balance = web3.eth.get_balance(agent_address)
    except Exception as exc:
        print(f"   ⚠️  Could not fetch balance for {agent_address}: {exc}")
        return True

    if current_balance >= min_balance:
        return True

    print(
        f"   ⚠️  Web3 RPC reports {web3.from_wei(current_balance, 'ether')} HBAR for {agent_address}. "
        "Ensure the agent wallet is funded before proceeding."
    )
    return True


def _submit_ethereum_transaction(raw_tx: bytes) -> bool:
    """Submit a signed Ethereum transaction via the Hedera EthereumTransaction wrapper."""
    try:
        tx = EthereumTransaction()
        tx.set_ethereum_data(raw_tx)
        tx.set_max_gas_allowed(Hbar(MAX_GAS_ALLOWANCE_HBAR).to_tinybars())

        response = tx.execute(hedera_client)
        receipt = response.get_receipt(hedera_client) if hasattr(response, "get_receipt") else response
        status = getattr(receipt, "status", None)
        status_name = getattr(status, "name", None)
        if status_name is None and isinstance(status, int):
            try:
                status_name = ResponseCode(status).name
            except ValueError:
                status_name = str(status)

        if status_name != "SUCCESS":
            print(f"   ❌ Hedera execution status: {status_name}")
            return False

        return True
    except Exception as exc:  # noqa: BLE001
        print(f"   ❌ Hedera EthereumTransaction failed: {exc}")
        return False


def register_agent_on_chain(domain: str, agent_address: str = None, metadata_uri: str = None, registry_agent_id: int | None = None):
    """
    Register an agent on the NEW identity registry with metadata.

    Args:
        domain: Agent domain/identifier (e.g., "problem-framer-001")
        agent_address: Ethereum address (defaults to unique generated address)
        metadata_uri: URI to agent metadata JSON file

    Returns:
        Transaction receipt or None if failed
    """
    metadata_uri = metadata_uri or f"{METADATA_BASE_URL.rstrip('/')}/{domain}.json"
    metadata_uri = metadata_uri.strip()

    existing_agent_id = registry_agent_id
    existing_metadata_uri = None
    existing_agent_address = None

    if existing_agent_id:
        try:
            on_chain_agent = identity_registry.functions.getAgent(existing_agent_id).call()
            if len(on_chain_agent) > 2:
                existing_agent_address = on_chain_agent[2]
            if len(on_chain_agent) > 3:
                existing_metadata_uri = on_chain_agent[3]
        except Exception as exc:
            print(f"   ⚠️  Could not load existing agent {existing_agent_id}: {exc}")
    else:
        try:
            existing = identity_registry.functions.resolveByDomain(domain).call()
            if existing and existing[0] > 0:
                existing_agent_id = existing[0]
                if len(existing) > 2:
                    existing_agent_address = existing[2]
                if len(existing) > 3:
                    existing_metadata_uri = existing[3]
        except Exception:
            existing_agent_id = None

    if existing_agent_id:
        if (existing_metadata_uri or "").strip() == metadata_uri:
            print(f"   ✅ Agent '{domain}' metadata already up to date (ID: {existing_agent_id})")
            return {"status": "already_registered", "agent_id": existing_agent_id}

        print(f"   🔁 Updating metadata for agent ID {existing_agent_id}")
        return _update_agent_metadata(existing_agent_id, metadata_uri, domain, existing_agent_address)

    if agent_address is None:
        agent_address = _derive_agent_account(domain).address

    print(f"   🔐 Agent address: {agent_address}")
    print(f"   📄 Metadata URI: {metadata_uri}")

    try:
        # Get the required registration fee from contract
        try:
            required_fee = identity_registry.functions.REGISTRATION_FEE().call()
            print(f"   💰 Required fee: {web3.from_wei(required_fee, 'ether')} HBAR ({required_fee} wei)")
        except Exception as e:
            print(f"   ⚠️  Could not fetch registration fee: {e}")
            required_fee = web3.to_wei(0.005, "ether")

        # Estimate gas first
        try:
            gas_estimate = identity_registry.functions.newAgent(
                domain, agent_address, metadata_uri
            ).estimate_gas({
                "from": wallet_address,
                "value": required_fee,
            })
            print(f"   📊 Estimated gas: {gas_estimate}")
        except Exception as e:
            print(f"   ⚠️  Gas estimation failed: {e}")
            print(f"   This might mean the contract doesn't have the 3-parameter newAgent function")
            raise

        # Build transaction
        tx = identity_registry.functions.newAgent(
            domain, agent_address, metadata_uri
        ).build_transaction({
            "from": wallet_address,
            "value": required_fee,
            "nonce": web3.eth.get_transaction_count(wallet_address),
            "gas": min(500000, gas_estimate + 50000),
            "gasPrice": web3.eth.gas_price,
        })

        # Sign and send
        signed_tx = web3.eth.account.sign_transaction(tx, PRIVATE_KEY)
        tx_hash = web3.eth.send_raw_transaction(signed_tx.raw_transaction)

        print(f"   ⏳ TX: {tx_hash.hex()}")

        # Wait for confirmation
        receipt = web3.eth.wait_for_transaction_receipt(tx_hash, timeout=120)

        if receipt['status'] == 1:
            print(f"   ✅ Registered successfully!")
            new_agent_id = None
            try:
                resolved = identity_registry.functions.resolveByDomain(domain).call()
                if resolved and resolved[0] > 0:
                    new_agent_id = resolved[0]
            except Exception:
                pass
            return {
                "status": "registered",
                "agent_id": new_agent_id,
                "tx": tx_hash.hex(),
            }
        else:
            print(f"   ❌ Transaction failed")
            print(f"   Gas used: {receipt.get('gasUsed', 'N/A')}")
            return None

    except Exception as e:
        print(f"   ❌ Error: {e}")
        return None


def _update_agent_metadata(agent_id: int, metadata_uri: str, domain: str, agent_address: str | None):
    """Update metadata URI for an already registered agent."""
    derived_account = _derive_agent_account(domain)

    if agent_address and derived_account.address.lower() != agent_address.lower():
        print(
            f"   ❌ Cannot update metadata for agent ID {agent_id}; "
            "derived key does not match on-chain address."
        )
        return None

    if not _ensure_agent_balance(derived_account.address):
        print("   ❌ Unable to fund agent wallet for metadata update.")
        return None

    try:
        gas_estimate = identity_registry.functions.updateMetadata(agent_id, metadata_uri).estimate_gas(
            {"from": derived_account.address}
        )
        print(f"   📊 Estimated gas (update): {gas_estimate}")
    except Exception as exc:
        print(f"   ⚠️  Gas estimation for metadata update failed: {exc}")
        return None

    try:
        gas_limit = min(400000, gas_estimate + 50000)
        base_fee = web3.eth.gas_price
        priority_fee = web3.to_wei(PRIORITY_FEE_GWEI, "gwei")
        max_fee = base_fee + priority_fee

        tx = identity_registry.functions.updateMetadata(agent_id, metadata_uri).build_transaction(
            {
                "chainId": web3.eth.chain_id,
                "nonce": _get_next_nonce(derived_account.address),
                "gas": gas_limit,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "type": 2,
                "value": 0,
            }
        )
        signed_tx = web3.eth.account.sign_transaction(tx, derived_account.key)
        tx_hash = signed_tx.hash.hex()

        if not _submit_ethereum_transaction(signed_tx.raw_transaction):
            print("   ❌ Metadata update transaction failed")
            return None

        print(f"   ✅ Metadata updated on-chain for agent ID {agent_id} (tx {tx_hash})")
        return {
            "status": "metadata_updated",
            "agent_id": agent_id,
            "tx": tx_hash,
        }
    except Exception as exc:
        print(f"   ❌ Error updating metadata: {exc}")
        return None


def get_agent_count():
    """Get total number of registered agents."""
    try:
        count = identity_registry.functions.getAgentCount().call()
        return count
    except Exception as e:
        print(f"Error getting agent count: {e}")
        return 0


def list_registered_agents():
    """List all registered agents from on-chain registry."""
    print("\n" + "="*80)
    print("REGISTERED AGENTS ON IDENTITY REGISTRY")
    print("="*80)

    try:
        count = get_agent_count()
        print(f"\n📊 Total agents registered: {count}")

        if count == 0:
            print("\n⚠️  No agents registered yet")
            return

        print(f"\n{'ID':<8} {'Domain':<35} {'Address':<45}")
        print("-" * 80)

        for agent_id in range(1, count + 1):
            try:
                agent_info = identity_registry.functions.getAgent(agent_id).call()
                print(f"{agent_id:<8} {agent_info[1]:<35} {agent_info[2]:<45}")

                # If agent has metadata URI, display it
                if len(agent_info) > 3 and agent_info[3]:
                    print(f"         📄 Metadata: {agent_info[3]}")

            except Exception as e:
                print(f"{agent_id:<8} Error fetching agent: {e}")

    except Exception as e:
        print(f"\n❌ Error: {e}")


def test_registration():
    """Test registration with a single agent."""
    print("\n" + "="*80)
    print("TEST REGISTRATION")
    print("="*80)

    test_domain = "test-agent-" + str(int(os.time.time()) if hasattr(os, 'time') else "001")
    test_metadata_uri = f"{METADATA_BASE_URL}/test-agent.json"

    print(f"\n🧪 Testing with domain: {test_domain}")
    print(f"📄 Metadata URI: {test_metadata_uri}")

    result = register_agent_on_chain(test_domain, metadata_uri=test_metadata_uri)

    if result:
        print("\n✅ Test registration successful!")
    else:
        print("\n❌ Test registration failed")


def register_all_agents():
    """Register all agents from database to on-chain registry with metadata."""

    print("\n" + "="*80)
    print("AGENT REGISTRATION WITH METADATA")
    print("="*80)

    # Load agents from database
    db = SessionLocal()
    try:
        agents = db.query(AgentModel).filter(AgentModel.status == "active").all()

        if not agents:
            print("\n❌ No active agents found in database")
            print("   Run: python scripts/register_all_agents.py first")
            return

        print(f"\n📋 Found {len(agents)} active agents")
        print(f"💰 Estimated cost: {len(agents) * 0.005} HBAR (0.005 per agent)")
        print(f"📄 Metadata base URL: {METADATA_BASE_URL}")

        # Check balance
        balance = web3.eth.get_balance(wallet_address)
        balance_eth = float(web3.from_wei(balance, 'ether'))
        required = len(agents) * 0.005

        if balance_eth < required:
            print(f"\n⚠️  Warning: Insufficient balance!")
            print(f"   Required: {required} HBAR")
            print(f"   Available: {balance_eth} HBAR")

        print("\n" + "-"*80)
        print("Starting registration...")
        print("-"*80)

        registered = 0
        metadata_updates = 0
        already_registered = 0
        failed = 0

        for i, agent in enumerate(agents, 1):
            print(f"\n[{i}/{len(agents)}] {agent.name} ({agent.agent_id})")

            # Use agent_id as domain (unique identifier)
            domain = agent.agent_id

            meta = agent.meta or {}
            metadata_uri = (
                agent.erc8004_metadata_uri
                or meta.get("metadata_gateway_url")
                or meta.get("metadata_public_url")
                or f"{METADATA_BASE_URL.rstrip('/')}/{domain}.json"
            )

            registry_agent_id = meta.get("registry_agent_id")
            try:
                registry_agent_id = int(registry_agent_id) if registry_agent_id is not None else None
            except (TypeError, ValueError):
                registry_agent_id = None

            # Don't pass agent_address - let it generate unique address
            result = register_agent_on_chain(
                domain,
                metadata_uri=metadata_uri,
                registry_agent_id=registry_agent_id,
            )

            if result:
                status = result.get("status") if isinstance(result, dict) else None
                if status == "already_registered":
                    already_registered += 1
                elif status == "metadata_updated":
                    metadata_updates += 1
                else:
                    registered += 1
            else:
                failed += 1

        # Summary
        print("\n" + "="*80)
        print("REGISTRATION COMPLETE")
        print("="*80)
        print(f"\n✅ Newly registered: {registered}")
        print(f"🔁 Metadata updated: {metadata_updates}")
        print(f"⚠️  Already registered: {already_registered}")
        print(f"❌ Failed: {failed}")

        # Get on-chain count
        try:
            total_on_chain = get_agent_count()
            print(f"\n📊 Total agents on-chain: {total_on_chain}")
        except Exception as e:
            print(f"\n⚠️  Could not get on-chain count: {e}")

    finally:
        db.close()


# -------- MAIN --------

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python scripts/register_agents_with_metadata.py test       # Test with one agent")
        print("  python scripts/register_agents_with_metadata.py list       # List registered agents")
        print("  python scripts/register_agents_with_metadata.py register   # Register all agents")
        sys.exit(1)

    command = sys.argv[1].lower()

    if command == "test":
        test_registration()
    elif command == "list":
        list_registered_agents()
    elif command == "register":
        register_all_agents()
    else:
        print(f"❌ Unknown command: {command}")
        print("\nValid commands: test, list, register")
        sys.exit(1)
