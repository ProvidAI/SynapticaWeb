"""Reusable helpers for registering agents on the Hedera identity registry."""

from __future__ import annotations

import hashlib
import json
import logging
import os
import threading
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional

from dotenv import load_dotenv

load_dotenv()

logger = logging.getLogger(__name__)

try:  # pragma: no cover - optional dependency
    from web3 import Web3
    from web3.types import TxReceipt
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    Web3 = None  # type: ignore[assignment]
    TxReceipt = Dict[str, Any]  # type: ignore[assignment]
    _WEB3_IMPORT_ERROR = exc
else:  # pragma: no cover - exercised in integration
    _WEB3_IMPORT_ERROR = None

try:  # pragma: no cover - optional dependency
    from eth_account import Account
    from eth_account.signers.local import LocalAccount
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    Account = None  # type: ignore[assignment]
    LocalAccount = Any  # type: ignore[assignment]
    _ACCOUNT_IMPORT_ERROR = exc
else:
    _ACCOUNT_IMPORT_ERROR = None

try:  # pragma: no cover - optional dependency
    from hiero_sdk_python import (
        Client as HederaClient,
        Network as HederaNetwork,
        AccountId as HederaAccountId,
        PrivateKey as HederaPrivateKey,
        EthereumTransaction,
        Hbar,
    )
    from hiero_sdk_python.response_code import ResponseCode
except ModuleNotFoundError as exc:  # pragma: no cover - optional dependency
    HederaClient = None  # type: ignore[assignment]
    HederaNetwork = None  # type: ignore[assignment]
    HederaAccountId = None  # type: ignore[assignment]
    HederaPrivateKey = None  # type: ignore[assignment]
    EthereumTransaction = None  # type: ignore[assignment]
    Hbar = None  # type: ignore[assignment]
    ResponseCode = None  # type: ignore[assignment]
    _HIERO_IMPORT_ERROR = exc
else:
    _HIERO_IMPORT_ERROR = None


class AgentRegistryConfigError(RuntimeError):
    """Raised when registry configuration (env, ABI, deps) is invalid."""


class AgentRegistryRegistrationError(RuntimeError):
    """Raised when on-chain registration fails."""


@dataclass
class AgentRegistryResult:
    """Outcome of a registry interaction."""

    status: str
    agent_id: Optional[int] = None
    tx_hash: Optional[str] = None
    metadata_uri: Optional[str] = None
    domain: Optional[str] = None


@dataclass
class AgentRegistrySettings:
    """Environment-driven configuration for the registry client."""

    rpc_url: str
    private_key: str
    hedera_account_id: str
    hedera_network: str
    contract_address: str
    metadata_base_url: str
    abi_path: Path
    max_gas_allowance_hbar: float
    priority_fee_gwei: float

    @classmethod
    def from_env(cls) -> "AgentRegistrySettings":
        rpc_url = os.getenv("HEDERA_RPC_URL", "https://testnet.hashio.io/api")
        private_key = os.getenv("HEDERA_PRIVATE_KEY")
        hedera_account_id = os.getenv("HEDERA_ACCOUNT_ID")
        hedera_network = os.getenv("HEDERA_NETWORK", "testnet")
        contract_address = os.getenv("IDENTITY_REGISTRY_ADDRESS") or os.getenv("IDENTITY_CONTRACT_ADDRESS")
        metadata_base_url = os.getenv("METADATA_BASE_URL", "https://providai.io/metadata")
        abi_env_path = os.getenv("IDENTITY_REGISTRY_ABI")

        if not private_key or private_key == "your_hedera_private_key_here":
            raise AgentRegistryConfigError("HEDERA_PRIVATE_KEY is not configured")
        if not hedera_account_id:
            raise AgentRegistryConfigError("HEDERA_ACCOUNT_ID is not configured")
        if not contract_address:
            raise AgentRegistryConfigError(
                "IDENTITY_REGISTRY_ADDRESS (or IDENTITY_CONTRACT_ADDRESS) is not configured"
            )

        abi_path = Path(abi_env_path) if abi_env_path else Path(__file__).resolve().parents[1] / "contracts" / "IdentityRegistry.sol" / "IdentityRegistry.json"
        if not abi_path.exists():
            raise AgentRegistryConfigError(f"IdentityRegistry ABI not found at {abi_path}")

        max_gas_allowance = float(os.getenv("AGENT_METADATA_MAX_GAS_HBAR", "5.0"))
        priority_fee = float(os.getenv("AGENT_METADATA_PRIORITY_FEE_GWEI", "2.0"))

        return cls(
            rpc_url=rpc_url,
            private_key=private_key,
            hedera_account_id=hedera_account_id,
            hedera_network=hedera_network,
            contract_address=contract_address,
            metadata_base_url=metadata_base_url,
            abi_path=abi_path,
            max_gas_allowance_hbar=max_gas_allowance,
            priority_fee_gwei=priority_fee,
        )


def _load_hedera_private_key(value: str):  # pragma: no cover - depends on hiero_sdk_python
    raw = value.strip()
    if raw.startswith("0x"):
        raw = raw[2:]
    if len(raw) == 64 and HederaPrivateKey is not None:
        return HederaPrivateKey.from_bytes_ecdsa(bytes.fromhex(raw))
    if HederaPrivateKey is None:
        raise AgentRegistryConfigError(
            "hiero_sdk_python is required to derive Hedera keys but is not installed"
        ) from _HIERO_IMPORT_ERROR
    return HederaPrivateKey.from_string(raw)


class AgentRegistryClient:
    """Wrapper around the Hedera IdentityRegistry contract."""

    def __init__(self, settings: AgentRegistrySettings):
        self.settings = settings
        if Web3 is None:
            raise AgentRegistryConfigError("web3.py is required for registry access") from _WEB3_IMPORT_ERROR
        if Account is None:
            raise AgentRegistryConfigError("eth-account is required for registry access") from _ACCOUNT_IMPORT_ERROR
        if HederaClient is None:
            raise AgentRegistryConfigError(
                "hiero_sdk_python is required for registry access"
            ) from _HIERO_IMPORT_ERROR

        self.web3 = Web3(Web3.HTTPProvider(settings.rpc_url))
        if not self.web3.is_connected():
            raise AgentRegistryConfigError("Failed to connect to Hedera RPC endpoint")

        self.account: LocalAccount = self.web3.eth.account.from_key(settings.private_key)
        self.wallet_address = self.account.address

        self.identity_registry = self._load_contract(settings.abi_path, settings.contract_address)
        self.hedera_client = self._build_hedera_client()

        self._nonce_cache: Dict[str, int] = {}
        self._lock = threading.Lock()

    def _load_contract(self, abi_path: Path, contract_address: str):
        with abi_path.open("r", encoding="utf-8") as fh:
            contract_data = json.load(fh)
        abi = contract_data.get("abi")
        if not abi:
            raise AgentRegistryConfigError(f"ABI definition missing in {abi_path}")
        return self.web3.eth.contract(address=contract_address, abi=abi)

    def _build_hedera_client(self):  # pragma: no cover - network side effects
        network = (
            self.settings.hedera_network
            if self.settings.hedera_network in {"mainnet", "testnet", "previewnet"}
            else "testnet"
        )
        hedera_client = HederaClient(HederaNetwork(network))
        hedera_client.set_operator(
            HederaAccountId.from_string(self.settings.hedera_account_id),
            _load_hedera_private_key(self.settings.private_key),
        )
        return hedera_client

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def register_agent(
        self,
        domain: str,
        *,
        metadata_uri: Optional[str] = None,
        agent_address: Optional[str] = None,
        registry_agent_id: Optional[int] = None,
    ) -> AgentRegistryResult:
        metadata_uri = (metadata_uri or self._default_metadata_uri(domain)).strip()
        if not metadata_uri:
            raise AgentRegistryRegistrationError("Metadata URI is required")

        with self._lock:
            return self._register_locked(domain, metadata_uri, agent_address, registry_agent_id)

    def get_agent_count(self) -> int:
        try:
            return int(self.identity_registry.functions.getAgentCount().call())
        except Exception as exc:  # noqa: BLE001
            raise AgentRegistryRegistrationError(f"Failed to load agent count: {exc}") from exc

    def get_registration_fee(self) -> int:
        """Return the current registration fee in wei."""

        return self._get_registration_fee()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _register_locked(
        self,
        domain: str,
        metadata_uri: str,
        agent_address: Optional[str],
        registry_agent_id: Optional[int],
    ) -> AgentRegistryResult:
        existing_agent_id = registry_agent_id
        existing_metadata_uri: Optional[str] = None
        existing_agent_address: Optional[str] = None

        if existing_agent_id:
            try:
                on_chain_agent = self.identity_registry.functions.getAgent(existing_agent_id).call()
                if len(on_chain_agent) > 2:
                    existing_agent_address = on_chain_agent[2]
                if len(on_chain_agent) > 3:
                    existing_metadata_uri = on_chain_agent[3]
            except Exception as exc:  # noqa: BLE001
                logger.warning("Could not load existing agent %s: %s", existing_agent_id, exc)
        else:
            try:
                existing = self.identity_registry.functions.resolveByDomain(domain).call()
                if existing and existing[0] > 0:
                    existing_agent_id = existing[0]
                    if len(existing) > 2:
                        existing_agent_address = existing[2]
                    if len(existing) > 3:
                        existing_metadata_uri = existing[3]
            except Exception as exc:  # noqa: BLE001
                logger.debug("Domain resolve failed for %s: %s", domain, exc)

        if existing_agent_id:
            if (existing_metadata_uri or "").strip() == metadata_uri:
                return AgentRegistryResult(
                    status="already_registered",
                    agent_id=existing_agent_id,
                    metadata_uri=metadata_uri,
                    domain=domain,
                )
            return self._update_agent_metadata(existing_agent_id, metadata_uri, domain, existing_agent_address)

        agent_address = agent_address or self._derive_agent_account(domain).address
        required_fee = self._get_registration_fee()

        try:
            gas_estimate = self.identity_registry.functions.newAgent(
                domain, agent_address, metadata_uri
            ).estimate_gas({
                "from": self.wallet_address,
                "value": required_fee,
            })
        except Exception as exc:  # noqa: BLE001
            raise AgentRegistryRegistrationError(f"Gas estimation failed: {exc}") from exc

        tx = self.identity_registry.functions.newAgent(
            domain, agent_address, metadata_uri
        ).build_transaction({
            "from": self.wallet_address,
            "value": required_fee,
            "nonce": self.web3.eth.get_transaction_count(self.wallet_address),
            "gas": min(500_000, gas_estimate + 50_000),
            "gasPrice": self.web3.eth.gas_price,
        })

        try:
            signed_tx = self.web3.eth.account.sign_transaction(tx, self.settings.private_key)
            tx_hash = self.web3.eth.send_raw_transaction(signed_tx.raw_transaction)
            receipt: TxReceipt = self.web3.eth.wait_for_transaction_receipt(tx_hash, timeout=180)
        except Exception as exc:  # noqa: BLE001
            raise AgentRegistryRegistrationError(f"Failed to submit registration tx: {exc}") from exc

        if int(receipt.get("status", 0)) != 1:
            raise AgentRegistryRegistrationError(
                f"Registration transaction reverted (gas used {receipt.get('gasUsed')})"
            )

        new_agent_id: Optional[int] = None
        try:
            resolved = self.identity_registry.functions.resolveByDomain(domain).call()
            if resolved and resolved[0] > 0:
                new_agent_id = resolved[0]
        except Exception as exc:  # noqa: BLE001
            logger.warning("Failed to resolve domain %s after registration: %s", domain, exc)

        return AgentRegistryResult(
            status="registered",
            agent_id=new_agent_id,
            tx_hash=tx_hash.hex(),
            metadata_uri=metadata_uri,
            domain=domain,
        )

    def _update_agent_metadata(
        self,
        agent_id: int,
        metadata_uri: str,
        domain: str,
        agent_address: Optional[str],
    ) -> AgentRegistryResult:
        derived_account = self._derive_agent_account(domain)
        if agent_address and derived_account.address.lower() != agent_address.lower():
            raise AgentRegistryRegistrationError(
                "Derived key does not match on-chain agent address; cannot update metadata."
            )

        if not self._ensure_agent_balance(derived_account.address):
            raise AgentRegistryRegistrationError(
                f"Insufficient balance for agent key {derived_account.address}"
            )

        try:
            gas_estimate = self.identity_registry.functions.updateMetadata(agent_id, metadata_uri).estimate_gas(
                {"from": derived_account.address}
            )
        except Exception as exc:  # noqa: BLE001
            raise AgentRegistryRegistrationError(f"Gas estimation failed for metadata update: {exc}") from exc

        gas_limit = min(400_000, gas_estimate + 50_000)
        base_fee = self.web3.eth.gas_price
        priority_fee = self.web3.to_wei(self.settings.priority_fee_gwei, "gwei")
        max_fee = base_fee + priority_fee

        tx = self.identity_registry.functions.updateMetadata(agent_id, metadata_uri).build_transaction(
            {
                "chainId": self.web3.eth.chain_id,
                "nonce": self._get_next_nonce(derived_account.address),
                "gas": gas_limit,
                "maxFeePerGas": max_fee,
                "maxPriorityFeePerGas": priority_fee,
                "type": 2,
                "value": 0,
            }
        )

        try:
            signed_tx = self.web3.eth.account.sign_transaction(tx, derived_account.key)
        except Exception as exc:  # noqa: BLE001
            raise AgentRegistryRegistrationError(f"Failed to sign metadata tx: {exc}") from exc

        tx_hash = signed_tx.hash.hex()

        if not self._submit_ethereum_transaction(signed_tx.raw_transaction):
            raise AgentRegistryRegistrationError("Hedera EthereumTransaction submission failed")

        return AgentRegistryResult(
            status="metadata_updated",
            agent_id=agent_id,
            tx_hash=tx_hash,
            metadata_uri=metadata_uri,
            domain=domain,
        )

    def _submit_ethereum_transaction(self, raw_tx: bytes) -> bool:  # pragma: no cover - network side effects
        try:
            tx = EthereumTransaction()
            tx.set_ethereum_data(raw_tx)
            tx.set_max_gas_allowed(Hbar(self.settings.max_gas_allowance_hbar).to_tinybars())

            response = tx.execute(self.hedera_client)
            receipt = response.get_receipt(self.hedera_client) if hasattr(response, "get_receipt") else response
            status = getattr(receipt, "status", None)
            status_name = getattr(status, "name", None)
            if status_name is None and isinstance(status, int) and ResponseCode is not None:
                try:
                    status_name = ResponseCode(status).name
                except ValueError:
                    status_name = str(status)

            if status_name != "SUCCESS":
                logger.error("Hedera EthereumTransaction failed with status %s", status_name)
                return False
            return True
        except Exception as exc:  # noqa: BLE001
            logger.error("Failed to execute Hedera EthereumTransaction: %s", exc)
            return False

    def _derive_agent_account(self, domain: str):
        seed = hashlib.sha256(domain.encode()).hexdigest()
        return Account.from_key("0x" + seed)

    def _ensure_agent_balance(self, address: str) -> bool:  # pragma: no cover - network state
        min_balance = self.web3.to_wei(0.002, "ether")
        try:
            current_balance = self.web3.eth.get_balance(address)
        except Exception as exc:  # noqa: BLE001
            logger.warning("Could not fetch balance for %s: %s", address, exc)
            return True
        if current_balance >= min_balance:
            return True
        logger.warning(
            "Derived agent wallet %s has balance %s < %s", address, current_balance, min_balance
        )
        return False

    def _get_registration_fee(self) -> int:
        try:
            return int(self.identity_registry.functions.REGISTRATION_FEE().call())
        except Exception as exc:  # noqa: BLE001
            logger.debug("REGISTRATION_FEE lookup failed: %s", exc)
            return int(self.web3.to_wei(0.005, "ether"))

    def _default_metadata_uri(self, domain: str) -> str:
        return f"{self.settings.metadata_base_url.rstrip('/')}/{domain}.json"

    def _get_next_nonce(self, address: str) -> int:
        try:
            network_nonce = self.web3.eth.get_transaction_count(address)
        except Exception:  # noqa: BLE001
            network_nonce = 0
        cached = self._nonce_cache.get(address)
        next_nonce = network_nonce if cached is None else max(network_nonce, cached)
        self._nonce_cache[address] = next_nonce + 1
        return next_nonce


_default_client: Optional[AgentRegistryClient] = None
_client_lock = threading.Lock()


def get_registry_client(force_refresh: bool = False) -> AgentRegistryClient:
    """Return a cached registry client configured from environment variables."""

    global _default_client
    with _client_lock:
        if force_refresh or _default_client is None:
            settings = AgentRegistrySettings.from_env()
            _default_client = AgentRegistryClient(settings)
        return _default_client
