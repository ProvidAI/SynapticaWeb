"""Agent metadata builder and Pinata publishing helper."""

from __future__ import annotations

import json
import logging
import os
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import httpx

logger = logging.getLogger(__name__)

PINATA_PIN_JSON_URL = "https://api.pinata.cloud/pinning/pinJSONToIPFS"
METADATA_DIR = Path(__file__).resolve().parent.parent.parent / "agent_metadata"


@dataclass(slots=True)
class PinataUploadResult:
    """Details about a Pinata upload."""

    cid: str
    ipfs_uri: str
    gateway_url: str
    pinata_url: str


@dataclass(slots=True)
class AgentMetadataPayload:
    """Structured representation of metadata inputs."""

    agent_id: str
    name: str
    description: str
    endpoint_url: str
    capabilities: List[str]
    pricing_rate: float
    pricing_currency: str = "HBAR"
    pricing_rate_type: str = "per_task"
    categories: Optional[List[str]] = None
    contact_email: Optional[str] = None
    logo_url: Optional[str] = None
    health_check_url: Optional[str] = None
    hedera_account: Optional[str] = None
    supported_trust: Optional[List[str]] = None
    registrations: Optional[List[Dict[str, Any]]] = None
    metadata_version: str = "1.0.0"


class PinataCredentialsError(RuntimeError):
    """Raised when Pinata credentials are missing."""


class PinataUploadError(RuntimeError):
    """Raised when a Pinata upload fails."""


def _ensure_metadata_dir() -> None:
    """Ensure the agent metadata directory exists."""
    METADATA_DIR.mkdir(parents=True, exist_ok=True)


def save_agent_metadata_locally(agent_id: str, metadata: Dict[str, Any]) -> Path:
    """
    Persist metadata JSON for audit purposes.

    Args:
        agent_id: Agent identifier used for the filename.
        metadata: Metadata payload to serialize.

    Returns:
        Path to the persisted metadata file.
    """
    _ensure_metadata_dir()

    path = METADATA_DIR / f"{agent_id}.json"
    with path.open("w", encoding="utf-8") as fh:
        json.dump(metadata, fh, indent=2)

    return path


def build_agent_metadata_payload(data: AgentMetadataPayload) -> Dict[str, Any]:
    """
    Construct an ERC-8004 compliant metadata document.

    Args:
        data: Structured agent inputs.

    Returns:
        Serializable metadata dictionary.
    """
    now_iso = datetime.now(timezone.utc).isoformat()

    def _append_endpoint(
        name: str,
        endpoint: Optional[str],
        *,
        method: Optional[str] = None,
        description: Optional[str] = None,
    ) -> None:
        if not endpoint:
            return
        entry: Dict[str, Any] = {
            "name": name,
            "type": name.lower(),
            "endpoint": endpoint,
            "url": endpoint,
        }
        if method:
            entry["method"] = method
        if description:
            entry["description"] = description
        endpoints.append(entry)

    endpoints: List[Dict[str, Any]] = []

    _append_endpoint(
        "primary",
        data.endpoint_url,
        method="POST",
        description="Primary execution endpoint",
    )

    _append_endpoint(
        "health",
        data.health_check_url,
        method="GET",
        description="Health check endpoint",
    )

    if data.hedera_account:
        _append_endpoint(
            "agentWallet",
            data.hedera_account,
            description="Wallet reference for settlements",
        )

    if not endpoints:
        raise ValueError("At least one endpoint is required for ERC-8004 metadata")

    supported_trust = data.supported_trust
    if supported_trust is None:
        supported_trust = ["reputation"]

    registrations = data.registrations or []

    metadata: Dict[str, Any] = {
        "type": "https://eips.ethereum.org/EIPS/eip-8004#registration-v1",
        "agentId": data.agent_id,
        "name": data.name,
        "description": data.description,
        "image": data.logo_url or "https://providai.io/assets/agent-placeholder.png",
        "capabilities": data.capabilities,
        "categories": data.categories or [],
        "pricing": {
            "rate": data.pricing_rate,
            "currency": data.pricing_currency,
            "rateType": data.pricing_rate_type,
        },
        "supportedTrust": supported_trust,
        "endpoints": endpoints,
        "contact": {"email": data.contact_email} if data.contact_email else {},
        "agentWallet": data.hedera_account or "",
        "registrations": registrations,
        "createdAt": now_iso,
        "updatedAt": now_iso,
        "metadataVersion": data.metadata_version,
    }

    return metadata


def _get_pinata_headers() -> Dict[str, str]:
    """Return Pinata authentication headers or raise if missing."""
    api_key = os.getenv("PINATA_API_KEY")
    secret_key = os.getenv("PINATA_SECRET_KEY")

    if not api_key or not secret_key:
        raise PinataCredentialsError("Pinata credentials are not configured")

    return {
        "pinata_api_key": api_key,
        "pinata_secret_api_key": secret_key,
        "Content-Type": "application/json",
    }


async def publish_agent_metadata(agent_id: str, metadata: Dict[str, Any]) -> PinataUploadResult:
    """
    Persist metadata locally and upload to Pinata.

    Args:
        agent_id: Agent identifier.
        metadata: Metadata payload to upload.

    Returns:
        PinataUploadResult describing the upload.

    Raises:
        PinataCredentialsError if credentials missing.
        PinataUploadError if upload fails.
    """
    path = save_agent_metadata_locally(agent_id, metadata)
    try:
        headers = _get_pinata_headers()

        payload = {
            "pinataMetadata": {
                "name": f"{agent_id}.json",
                "keyvalues": {
                    "project": "ProvidAI",
                    "type": "agent_metadata",
                },
            },
            "pinataContent": metadata,
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                PINATA_PIN_JSON_URL,
                headers=headers,
                json=payload,
            )
        response.raise_for_status()
        result = response.json()
    except PinataCredentialsError:
        path.unlink(missing_ok=True)
        raise
    except httpx.HTTPStatusError as exc:
        path.unlink(missing_ok=True)
        body = exc.response.text
        logger.error("Pinata upload failed: %s - %s", exc, body)
        raise PinataUploadError(f"Pinata upload failed: {exc.response.status_code} {body}") from exc
    except Exception as exc:  # noqa: BLE001
        path.unlink(missing_ok=True)
        logger.exception("Unexpected error uploading metadata for %s", agent_id)
        raise PinataUploadError(str(exc)) from exc

    cid = result.get("IpfsHash")
    if not cid:
        logger.error("Pinata response missing IpfsHash: %s", result)
        path.unlink(missing_ok=True)
        raise PinataUploadError("Pinata response missing IpfsHash")

    return PinataUploadResult(
        cid=cid,
        ipfs_uri=f"ipfs://{cid}",
        gateway_url=f"https://gateway.pinata.cloud/ipfs/{cid}",
        pinata_url=f"https://app.pinata.cloud/pinmanager?search={cid}",
    )
