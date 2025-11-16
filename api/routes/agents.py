"""Agent management routes for the marketplace and onboarding flow."""

from __future__ import annotations

import logging
import os
import re
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, Header, HTTPException, status
from pydantic import BaseModel, ConfigDict, EmailStr, Field, field_validator
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from shared.database import Agent, AgentReputation, get_db
from shared.registry_sync import (
    RegistrySyncError,
    ensure_registry_cache,
    get_registry_sync_status,
)
from shared.metadata import (
    AgentMetadataPayload,
    PinataCredentialsError,
    PinataUploadError,
    build_agent_metadata_payload,
    publish_agent_metadata,
)

router = APIRouter(prefix="/api/agents", tags=["agents"])

logger = logging.getLogger(__name__)
AUDIT_LOGGER = logging.getLogger("agent_registration")

AGENT_ID_PATTERN = re.compile(r"^[a-z0-9-]{3,50}$")
HEDERA_ACCOUNT_PATTERN = re.compile(r"^(0\.0\.\d+|0x[a-fA-F0-9]{40})$")
ALLOW_INSECURE_ENDPOINTS = os.getenv("AGENT_SUBMIT_ALLOW_HTTP", "1").lower() in {"1", "true", "yes"}


class AgentPricing(BaseModel):
    """Pricing information for an agent."""

    rate: float = Field(..., ge=0)
    currency: str = Field("HBAR", min_length=1, max_length=10)
    rate_type: str = Field("per_task", min_length=3, max_length=32)


class AgentResponse(BaseModel):
    """Shape of agent responses for the marketplace."""

    model_config = ConfigDict(from_attributes=True)

    agent_id: str
    name: str
    description: Optional[str] = None
    capabilities: List[str]
    categories: List[str]
    status: str
    endpoint_url: Optional[str] = None
    health_check_url: Optional[str] = None
    pricing: AgentPricing
    contact_email: Optional[str] = None
    logo_url: Optional[str] = None
    erc8004_metadata_uri: Optional[str] = None
    metadata_cid: Optional[str] = None
    metadata_gateway_url: Optional[str] = None
    hedera_account_id: Optional[str] = None
    created_at: Optional[str] = None


class AgentsListResponse(BaseModel):
    """List response for agents."""

    total: int
    agents: List[AgentResponse]
    sync_status: Optional[str] = None
    synced_at: Optional[str] = None


class AgentSubmissionRequest(BaseModel):
    """Payload for registering a new agent."""

    model_config = ConfigDict(extra="forbid")

    agent_id: str = Field(..., min_length=3, max_length=50)
    name: str = Field(..., min_length=3, max_length=120)
    description: str = Field(..., min_length=10, max_length=1_000)
    capabilities: List[str] = Field(..., min_length=1)
    categories: Optional[List[str]] = None
    endpoint_url: str
    health_check_url: Optional[str] = None
    base_rate: float = Field(..., gt=0)
    currency: str = Field("HBAR", min_length=1, max_length=10)
    rate_type: str = Field("per_task", min_length=3, max_length=32)
    hedera_account: Optional[str] = None
    logo_url: Optional[str] = None
    contact_email: Optional[EmailStr] = None

    @field_validator("agent_id")
    @classmethod
    def validate_agent_id(cls, value: str) -> str:
        """Ensure agent_id is a slug as required."""
        if not AGENT_ID_PATTERN.match(value):
            raise ValueError(
                "agent_id must be 3-50 characters of lowercase letters, numbers, or dashes"
            )
        return value

    @field_validator("capabilities")
    @classmethod
    def validate_capabilities(cls, value: List[str]) -> List[str]:
        """Ensure capability list is sane and trimmed."""
        cleaned = [cap.strip() for cap in value if cap.strip()]
        if not cleaned:
            raise ValueError("At least one capability is required")
        return cleaned

    @field_validator("categories")
    @classmethod
    def validate_categories(cls, value: Optional[List[str]]) -> List[str]:
        """Normalize categories list."""
        if not value:
            return []
        return [item.strip() for item in value if item.strip()]

    @field_validator("endpoint_url", "health_check_url")
    @classmethod
    def validate_endpoint(cls, value: Optional[str], _info) -> Optional[str]:
        """Ensure endpoints use HTTPS unless explicitly allowed."""
        if value is None:
            return value
        if not value.startswith(("http://", "https://")):
            raise ValueError("URL must start with http:// or https://")
        if (not value.startswith("https://")) and not ALLOW_INSECURE_ENDPOINTS:
            raise ValueError("URL must use HTTPS")
        return value

    @field_validator("hedera_account")
    @classmethod
    def validate_hedera_account(cls, value: Optional[str]) -> Optional[str]:
        """Validate Hedera account formatting."""
        if value is None or value.strip() == "":
            return None
        if not HEDERA_ACCOUNT_PATTERN.match(value.strip()):
            raise ValueError("Hedera account must match 0.0.x or 0x followed by 40 hex characters")
        return value.strip()

    @field_validator("logo_url")
    @classmethod
    def validate_logo_url(cls, value: Optional[str]) -> Optional[str]:
        """Basic validation for logo URL."""
        if value is None:
            return value
        if not value.startswith(("http://", "https://")):
            raise ValueError("Logo URL must start with http:// or https://")
        return value


class AgentSubmissionResponse(AgentResponse):
    """Extended response for agent creation."""

    metadata_gateway_url: Optional[str] = None
    metadata_cid: Optional[str] = None
    operator_checklist: List[str]
    message: str


def _require_admin_token(provided: Optional[str]) -> None:
    """Enforce optional admin header."""
    required = os.getenv("AGENT_SUBMIT_ADMIN_TOKEN")
    if not required:
        return
    if provided != required:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing admin token",
        )


def _coerce_rate(value: Any) -> float:
    """Attempt to convert a stored rate into a float."""
    if isinstance(value, (int, float)):
        return float(value)
    if isinstance(value, str):
        match = re.search(r"([0-9]*\.?[0-9]+)", value)
        if match:
            return float(match.group(1))
    return 0.0


def _extract_pricing(meta: Dict[str, Any]) -> AgentPricing:
    """Return pricing info, coercing stored metadata as needed."""
    pricing_dict = meta.get("pricing") or {}
    if not isinstance(pricing_dict, dict):
        pricing_dict = {}

    rate = _coerce_rate(pricing_dict.get("rate") or pricing_dict.get("base_rate"))
    currency = (
        pricing_dict.get("currency")
        or pricing_dict.get("currency_code")
        or "HBAR"
    )
    rate_type = (
        pricing_dict.get("rate_type")
        or pricing_dict.get("rateType")
        or pricing_dict.get("unit")
        or "per_task"
    )

    return AgentPricing(
        rate=rate,
        currency=currency,
        rate_type=rate_type,
    )


def _serialize_agent(agent: Agent) -> AgentResponse:
    """Convert an Agent ORM instance into API response."""
    meta: Dict[str, Any] = agent.meta or {}
    metadata_cid = meta.get("metadata_cid")

    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        description=agent.description,
        capabilities=agent.capabilities or [],
        categories=meta.get("categories") or [],
        status=agent.status or "inactive",
        endpoint_url=meta.get("endpoint_url"),
        health_check_url=meta.get("health_check_url"),
        pricing=_extract_pricing(meta),
        contact_email=meta.get("contact_email"),
        logo_url=meta.get("logo_url"),
        erc8004_metadata_uri=agent.erc8004_metadata_uri,
        metadata_cid=metadata_cid,
        metadata_gateway_url=meta.get("metadata_gateway_url")
        or (f"https://gateway.pinata.cloud/ipfs/{metadata_cid}" if metadata_cid else None),
        hedera_account_id=agent.hedera_account_id,
        created_at=agent.created_at.isoformat() if agent.created_at else None,
    )


def _is_registry_managed(agent: Agent) -> bool:
    """Return True when the agent was sourced from the registry sync."""
    meta: Dict[str, Any] = agent.meta or {}
    return bool(meta.get("registry_managed"))


@router.get("/", response_model=AgentsListResponse)
async def list_agents(db: Session = Depends(get_db)) -> AgentsListResponse:
    """List all registered agents."""
    sync_status = "unknown"
    synced_at = None
    try:
        ensure_registry_cache()
    except RegistrySyncError as exc:
        logger.warning("Registry sync failed: %s", exc)

    status_value, synced_dt = get_registry_sync_status()
    sync_status = status_value
    if synced_dt:
        synced_at = synced_dt.isoformat()

    agents = db.query(Agent).order_by(Agent.created_at.desc()).all()
    registry_agents = [agent for agent in agents if _is_registry_managed(agent)]
    source = registry_agents or agents
    serialized = [_serialize_agent(agent) for agent in source]

    return AgentsListResponse(
        total=len(serialized),
        agents=serialized,
        sync_status=sync_status,
        synced_at=synced_at,
    )


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: Session = Depends(get_db)) -> AgentResponse:
    """Retrieve a single agent."""
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()
    if not agent:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Agent not found")
    return _serialize_agent(agent)


@router.post("/", response_model=AgentSubmissionResponse, status_code=status.HTTP_201_CREATED)
async def register_agent(
    payload: AgentSubmissionRequest,
    db: Session = Depends(get_db),
    x_admin_token: Optional[str] = Header(default=None, alias="X-Admin-Token"),
) -> AgentSubmissionResponse:
    """Register a new HTTP agent and publish its metadata."""
    _require_admin_token(x_admin_token)

    existing = db.query(Agent).filter(Agent.agent_id == payload.agent_id).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=f"Agent '{payload.agent_id}' already exists",
        )

    meta: Dict[str, Any] = {
        "endpoint_url": payload.endpoint_url,
        "health_check_url": payload.health_check_url,
        "pricing": {
            "rate": payload.base_rate,
            "currency": payload.currency,
            "rate_type": payload.rate_type,
        },
        "categories": payload.categories or [],
        "contact_email": payload.contact_email,
        "logo_url": payload.logo_url,
    }

    agent = Agent(  # type: ignore[call-arg]
        agent_id=payload.agent_id,
        name=payload.name,
        agent_type="http",
        description=payload.description,
        capabilities=payload.capabilities,
        hedera_account_id=payload.hedera_account,
        status="active",
        meta=meta,
    )

    reputation = AgentReputation(
        agent_id=payload.agent_id,
        reputation_score=0.5,
        total_tasks=0,
        successful_tasks=0,
        failed_tasks=0,
        payment_multiplier=1.0,
    )

    db.add(agent)
    db.add(reputation)

    try:
        db.flush()
    except IntegrityError as exc:  # pragma: no cover - defensive
        db.rollback()
        logger.exception("Integrity error while registering agent %s", payload.agent_id)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(exc)) from exc

    metadata_payload = AgentMetadataPayload(
        agent_id=payload.agent_id,
        name=payload.name,
        description=payload.description,
        endpoint_url=payload.endpoint_url,
        capabilities=payload.capabilities,
        pricing_rate=payload.base_rate,
        pricing_currency=payload.currency,
        pricing_rate_type=payload.rate_type,
        categories=payload.categories,
        contact_email=payload.contact_email,
        logo_url=payload.logo_url,
        health_check_url=payload.health_check_url,
        hedera_account=payload.hedera_account,
    )
    metadata = build_agent_metadata_payload(metadata_payload)

    try:
        upload_result = await publish_agent_metadata(payload.agent_id, metadata)
    except PinataCredentialsError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Pinata credentials missing; configure PINATA_API_KEY and PINATA_SECRET_KEY.",
        ) from exc
    except PinataUploadError as exc:
        db.rollback()
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=str(exc),
        ) from exc

    agent.erc8004_metadata_uri = upload_result.ipfs_uri
    meta["metadata_cid"] = upload_result.cid
    meta["metadata_gateway_url"] = upload_result.gateway_url
    agent.meta = meta

    db.commit()
    db.refresh(agent)

    response = _serialize_agent(agent)
    operator_checklist = [
        "Review metadata JSON via provided gateway link.",
        "Optional: register on-chain using scripts/register_agents_with_metadata.py",
        "Verify endpoint responds to orchestrator/executor probes.",
    ]

    payload_summary = {
        "agent_id": payload.agent_id,
        "endpoint_url": payload.endpoint_url,
        "metadata_cid": upload_result.cid,
        "metadata_gateway_url": upload_result.gateway_url,
        "hedera_account": payload.hedera_account,
    }
    AUDIT_LOGGER.info("agent_registration", extra={"payload": payload_summary})

    response_payload = {
        **response.model_dump(),
        "metadata_gateway_url": upload_result.gateway_url,
        "metadata_cid": upload_result.cid,
        "operator_checklist": operator_checklist,
        "message": "Agent registered successfully.",
    }
    return AgentSubmissionResponse(**response_payload)
