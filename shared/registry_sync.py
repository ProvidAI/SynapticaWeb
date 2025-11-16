"""Helpers for syncing ERC-8004 registry data into the local cache."""

from __future__ import annotations

import json
import logging
import os
import threading
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Dict, Iterable, List, Optional, Tuple

import httpx
from sqlalchemy.orm import Session

from shared.database import (
    Agent,
    AgentReputation,
    AgentRegistrySyncState,
    SessionLocal,
)
from shared.handlers.identity_registry_handlers import get_all_domains, resolve_by_domain
from shared.handlers.reputation_registry_handlers import get_full_reputation_info
from shared.handlers.validation_registry_handlers import get_full_validation_info

logger = logging.getLogger(__name__)

_SYNC_LOCK = threading.Lock()


class RegistrySyncError(RuntimeError):
    """Raised when registry data cannot be synchronized."""


class RegistryUnavailableError(RegistrySyncError):
    """Raised when the registry contracts are unreachable or misconfigured."""


@dataclass
class AgentSnapshot:
    """Normalized snapshot of an on-chain agent."""

    agent_id: str
    name: str
    description: str
    capabilities: List[str]
    categories: List[str]
    metadata_uri: Optional[str]
    metadata_url: Optional[str]
    metadata_cid: Optional[str]
    hedera_account_id: Optional[str]
    endpoint_url: Optional[str]
    health_check_url: Optional[str]
    pricing: Dict[str, Any]
    contact_email: Optional[str]
    logo_url: Optional[str]
    registry_agent_id: int
    registry_domain: str
    registry_address: str
    metadata: Optional[Dict[str, Any]]
    reputation: Dict[str, Any]
    validation: Dict[str, Any]
    reputation_score: float


@dataclass
class RegistrySyncResult:
    """Summary of a registry sync run."""

    synced: int
    domains: List[str]
    status: str
    error: Optional[str] = None


def ensure_registry_cache(force: bool = False) -> Optional[RegistrySyncResult]:
    """
    Synchronize registry data when the cache is stale.

    Args:
        force: When True sync regardless of TTL.

    Returns:
        RegistrySyncResult if a sync was performed, otherwise None.
    """

    if not force and not _needs_sync():
        return None

    if not _SYNC_LOCK.acquire(blocking=False):
        logger.debug("Agent registry sync already running; skipping duplicate trigger.")
        return None

    try:
        return _sync_agents_from_registry()
    finally:
        _SYNC_LOCK.release()


def get_registry_sync_status() -> Tuple[str, Optional[datetime]]:
    """Return the last recorded sync status and timestamp."""

    session = SessionLocal()
    try:
        state = _get_or_create_state(session)
        return state.status or "never", state.last_successful_at
    finally:
        session.close()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _needs_sync() -> bool:
    ttl_seconds = _get_cache_ttl_seconds()
    session = SessionLocal()
    try:
        state = _get_or_create_state(session)
        if state.last_successful_at is None:
            return True
        delta = datetime.utcnow() - state.last_successful_at
        return delta.total_seconds() >= ttl_seconds
    finally:
        session.close()


def _sync_agents_from_registry() -> RegistrySyncResult:
    session = SessionLocal()
    now = datetime.utcnow()
    state = None
    try:
        state = _get_or_create_state(session)
        state.status = "running"
        state.last_attempted_at = now
        state.last_error = None
        session.commit()
    finally:
        session.close()

    try:
        snapshots = _fetch_registry_snapshots()
    except Exception as exc:  # noqa: BLE001
        session = SessionLocal()
        try:
            state = _get_or_create_state(session)
            state.status = "error"
            state.last_error = str(exc)
            state.last_attempted_at = datetime.utcnow()
            session.commit()
        finally:
            session.close()
        raise

    session = SessionLocal()
    synced_domains: List[str] = []
    try:
        synced_domains = _apply_snapshots(session, snapshots)
        state = _get_or_create_state(session)
        state.status = "ok"
        state.last_successful_at = datetime.utcnow()
        state.last_attempted_at = state.last_successful_at
        state.last_error = None
        session.commit()
    finally:
        session.close()

    return RegistrySyncResult(
        synced=len(synced_domains),
        domains=synced_domains,
        status="ok",
    )


def _fetch_registry_snapshots() -> List[AgentSnapshot]:
    try:
        domains = get_all_domains()
    except RuntimeError as exc:  # pragma: no cover - depends on web3 config
        raise RegistryUnavailableError("Identity registry unavailable. Check RPC/contract configuration.") from exc

    if not domains:
        logger.info("Identity registry returned no domains.")
        return []

    logger.info("Syncing %s agents from registry", len(domains))

    snapshots: List[AgentSnapshot] = []
    metadata_cache: Dict[str, Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]] = {}

    for domain in domains:
        domain = (domain or "").strip()
        if not domain:
            continue

        try:
            agent_info = resolve_by_domain(domain)
        except RuntimeError as exc:  # pragma: no cover - contract errors
            logger.warning("Failed to resolve domain %s: %s", domain, exc)
            continue

        if not agent_info:
            logger.warning("Domain %s resolved to empty agent info", domain)
            continue

        try:
            registry_agent_id = int(agent_info[0])
        except (TypeError, ValueError):
            logger.warning("Unexpected agent id for domain %s: %s", domain, agent_info)
            continue

        registry_domain = agent_info[1] or domain
        registry_address = agent_info[2]
        metadata_uri = agent_info[3] if len(agent_info) > 3 else None

        if metadata_uri in metadata_cache:
            metadata_payload, metadata_url, metadata_cid = metadata_cache[metadata_uri]
        else:
            metadata_payload, metadata_url, metadata_cid = _fetch_metadata(metadata_uri)
            metadata_cache[metadata_uri] = (metadata_payload, metadata_url, metadata_cid)

        rep_info = _safe_reputation_lookup(registry_agent_id)
        val_info = _safe_validation_lookup(registry_agent_id)

        snapshot = _build_snapshot(
            registry_agent_id=registry_agent_id,
            registry_domain=registry_domain,
            registry_address=registry_address,
            metadata_uri=metadata_uri,
            metadata_payload=metadata_payload,
            metadata_url=metadata_url,
            metadata_cid=metadata_cid,
            reputation=rep_info,
            validation=val_info,
        )
        snapshots.append(snapshot)

    return snapshots


def _apply_snapshots(session: Session, snapshots: List[AgentSnapshot]) -> List[str]:
    seen_ids: List[str] = []
    now = datetime.utcnow().isoformat()

    for snapshot in snapshots:
        agent = (
            session.query(Agent)
            .filter(Agent.agent_id == snapshot.agent_id)
            .one_or_none()
        )
        created = False
        if agent is None:
            agent = Agent(  # type: ignore[call-arg]
                agent_id=snapshot.agent_id,
                name=snapshot.name,
                agent_type="http",
                status="active",
                capabilities=snapshot.capabilities,
                description=snapshot.description,
            )
            session.add(agent)
            created = True

        agent.name = snapshot.name or snapshot.agent_id
        agent.description = snapshot.description
        agent.capabilities = snapshot.capabilities
        agent.erc8004_metadata_uri = snapshot.metadata_uri
        agent.hedera_account_id = snapshot.hedera_account_id
        agent.status = "active"

        meta = dict(agent.meta or {})
        meta.update(
            {
                "endpoint_url": snapshot.endpoint_url,
                "health_check_url": snapshot.health_check_url,
                "pricing": snapshot.pricing,
                "categories": snapshot.categories,
                "contact_email": snapshot.contact_email,
                "logo_url": snapshot.logo_url,
                "metadata_gateway_url": snapshot.metadata_url,
                "metadata_cid": snapshot.metadata_cid,
                "registry_agent_id": snapshot.registry_agent_id,
                "registry_domain": snapshot.registry_domain,
                "registry_address": snapshot.registry_address,
                "registry_synced_at": now,
                "registry_managed": True,
                "registry_metadata": snapshot.metadata,
                "registry_validation": snapshot.validation,
                "registry_reputation": snapshot.reputation,
            }
        )
        agent.meta = meta

        _upsert_reputation(session, snapshot)

        if created:
            session.flush()

        seen_ids.append(agent.agent_id)

    if seen_ids:
        inactive_candidates = (
            session.query(Agent)
            .filter(~Agent.agent_id.in_(seen_ids))
            .all()
        )
        for agent in inactive_candidates:
            agent_meta = agent.meta or {}
            if agent_meta.get("registry_managed"):
                agent.status = "inactive"
                agent_meta["registry_synced_at"] = now
                agent.meta = agent_meta

    session.commit()
    return seen_ids


def _upsert_reputation(session: Session, snapshot: AgentSnapshot) -> None:
    reputation = (
        session.query(AgentReputation)
        .filter(AgentReputation.agent_id == snapshot.agent_id)
        .one_or_none()
    )

    if reputation is None:
        reputation = AgentReputation(  # type: ignore[call-arg]
            agent_id=snapshot.agent_id,
            reputation_score=snapshot.reputation_score,
        )
        session.add(reputation)
    else:
        reputation.reputation_score = snapshot.reputation_score

    meta = dict(reputation.meta or {})
    meta.update(
        {
            "registry_reputation": snapshot.reputation,
            "registry_validation": snapshot.validation,
        }
    )
    reputation.meta = meta


def _build_snapshot(
    *,
    registry_agent_id: int,
    registry_domain: str,
    registry_address: str,
    metadata_uri: Optional[str],
    metadata_payload: Optional[Dict[str, Any]],
    metadata_url: Optional[str],
    metadata_cid: Optional[str],
    reputation: Dict[str, Any],
    validation: Dict[str, Any],
) -> AgentSnapshot:
    fields = _extract_metadata_fields(registry_domain, metadata_payload)
    reputation_score = _normalize_reputation_score(reputation)

    return AgentSnapshot(
        agent_id=fields["agent_id"],
        name=fields["name"],
        description=fields["description"],
        capabilities=fields["capabilities"],
        categories=fields["categories"],
        metadata_uri=metadata_uri,
        metadata_url=metadata_url,
        metadata_cid=metadata_cid,
        hedera_account_id=fields["hedera_account_id"],
        endpoint_url=fields["endpoint_url"],
        health_check_url=fields["health_check_url"],
        pricing=fields["pricing"],
        contact_email=fields["contact_email"],
        logo_url=fields["logo_url"],
        registry_agent_id=registry_agent_id,
        registry_domain=registry_domain,
        registry_address=registry_address,
        metadata=metadata_payload,
        reputation=reputation,
        validation=validation,
        reputation_score=reputation_score,
    )


def _extract_metadata_fields(domain: str, metadata: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    metadata = metadata or {}
    agent_id = (metadata.get("agentId") or domain or "").strip() or domain
    name = metadata.get("name") or agent_id
    description = metadata.get("description") or ""
    capabilities = _coerce_str_list(metadata.get("capabilities"))
    categories = _coerce_str_list(metadata.get("categories"))
    logo = metadata.get("image")
    contact = metadata.get("contact") or {}
    contact_email = contact.get("email")
    hedera_account = metadata.get("agentWallet") or metadata.get("agent_wallet")

    endpoints = metadata.get("endpoints") or []
    endpoint_url = _select_endpoint(endpoints, preferred_type="primary")
    health_url = _select_endpoint(endpoints, preferred_type="health")

    pricing = metadata.get("pricing") or {}
    normalized_pricing = {
        "rate": pricing.get("rate") or pricing.get("base_rate") or 0,
        "currency": pricing.get("currency") or pricing.get("currency_code") or "HBAR",
        "rate_type": pricing.get("rateType") or pricing.get("rate_type") or "per_task",
    }

    return {
        "agent_id": agent_id,
        "name": name,
        "description": description,
        "capabilities": capabilities,
        "categories": categories,
        "logo_url": logo,
        "contact_email": contact_email,
        "hedera_account_id": hedera_account,
        "endpoint_url": endpoint_url,
        "health_check_url": health_url,
        "pricing": normalized_pricing,
    }


def _coerce_str_list(value: Any) -> List[str]:
    if not value:
        return []
    if isinstance(value, str):
        return [value]
    if isinstance(value, Iterable):
        cleaned = []
        for item in value:
            if isinstance(item, str):
                stripped = item.strip()
                if stripped:
                    cleaned.append(stripped)
        return cleaned
    return []


def _select_endpoint(endpoints: Iterable[Dict[str, Any]], preferred_type: str) -> Optional[str]:
    for endpoint in endpoints:
        endpoint_type = (
            (endpoint.get("type") or "").lower()
            if isinstance(endpoint.get("type"), str)
            else ""
        )
        endpoint_name = (
            (endpoint.get("name") or "").lower()
            if isinstance(endpoint.get("name"), str)
            else ""
        )
        if preferred_type.lower() in {endpoint_type, endpoint_name}:
            return endpoint.get("url") or endpoint.get("endpoint")
    for endpoint in endpoints:
        url = endpoint.get("url") or endpoint.get("endpoint")
        if url:
            return url
    return None


def _normalize_reputation_score(reputation: Dict[str, Any]) -> float:
    if not reputation:
        return 0.0
    score = reputation.get("reputationScore") or reputation.get("score") or 0
    try:
        score = float(score)
    except (TypeError, ValueError):
        score = 0.0
    if score > 1:
        score = score / 100.0
    return max(0.0, min(1.0, score))


def _safe_reputation_lookup(agent_id: int) -> Dict[str, Any]:
    try:
        data = get_full_reputation_info(agent_id)
        return data or {}
    except RuntimeError as exc:  # pragma: no cover - depends on configuration
        logger.warning("Reputation registry unavailable for agent %s: %s", agent_id, exc)
        return {}


def _safe_validation_lookup(agent_id: int) -> Dict[str, Any]:
    try:
        data = get_full_validation_info(agent_id)
        return data or {}
    except RuntimeError as exc:  # pragma: no cover - depends on configuration
        logger.warning("Validation registry unavailable for agent %s: %s", agent_id, exc)
        return {}


def _fetch_metadata(metadata_uri: Optional[str]) -> Tuple[Optional[Dict[str, Any]], Optional[str], Optional[str]]:
    if not metadata_uri:
        return None, None, None

    resolved_url, cid = _resolve_metadata_uri(metadata_uri)
    if resolved_url is None:
        return None, None, cid

    try:
        with httpx.Client(timeout=10.0) as client:
            response = client.get(resolved_url)
            response.raise_for_status()
            if response.headers.get("Content-Type", "").startswith("application/json"):
                payload = response.json()
            else:
                payload = json.loads(response.text)
            return payload, resolved_url, cid
    except Exception as exc:  # noqa: BLE001
        logger.warning("Failed to fetch metadata %s: %s", resolved_url, exc)
        return None, resolved_url, cid


def _resolve_metadata_uri(metadata_uri: str) -> Tuple[Optional[str], Optional[str]]:
    metadata_uri = metadata_uri.strip()
    cid = None
    if metadata_uri.startswith("ipfs://"):
        cid = metadata_uri.replace("ipfs://", "", 1)
        gateway = os.getenv("AGENT_METADATA_GATEWAY_URL", "https://gateway.pinata.cloud/ipfs/")
        gateway = gateway.rstrip("/")
        return f"{gateway}/{cid}", cid
    if metadata_uri.startswith("http://") or metadata_uri.startswith("https://"):
        return metadata_uri, None
    return None, None


def _get_or_create_state(session: Session) -> AgentRegistrySyncState:
    state = session.query(AgentRegistrySyncState).order_by(AgentRegistrySyncState.id.asc()).first()
    if state:
        return state
    state = AgentRegistrySyncState(status="never")
    session.add(state)
    session.commit()
    session.refresh(state)
    return state


def _get_cache_ttl_seconds() -> int:
    value = os.getenv("AGENT_REGISTRY_CACHE_TTL_SECONDS", "300")
    try:
        ttl = int(value)
    except ValueError:
        ttl = 300
    return max(60, ttl)
