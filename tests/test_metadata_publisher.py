from datetime import datetime
from pathlib import Path

import json

from shared.metadata.publisher import (
    AgentMetadataPayload,
    build_agent_metadata_payload,
    save_agent_metadata_locally,
)


def test_build_agent_metadata_payload_shapes_endpoints():
    payload = AgentMetadataPayload(
        agent_id="test-agent",
        name="Test Agent",
        description="Performs test operations",
        endpoint_url="https://example.com/execute",
        health_check_url="https://example.com/health",
        capabilities=["analysis", "reporting"],
        pricing_rate=1.25,
        pricing_currency="HBAR",
        pricing_rate_type="per_task",
        categories=["Testing"],
        contact_email="ops@example.com",
        logo_url="https://example.com/logo.png",
        hedera_account="0.0.1234",
        registrations=[{"agentId": 42, "agentRegistry": "eip155:296:0xabc"}],
    )

    metadata = build_agent_metadata_payload(payload)

    assert metadata["type"] == "https://eips.ethereum.org/EIPS/eip-8004#registration-v1"
    assert metadata["agentId"] == "test-agent"
    assert metadata["pricing"]["rate"] == 1.25
    assert metadata["pricing"]["currency"] == "HBAR"
    assert metadata["supportedTrust"] == ["reputation"]
    assert metadata["contact"]["email"] == "ops@example.com"
    assert metadata["agentWallet"] == "0.0.1234"
    assert metadata["registrations"] == payload.registrations

    endpoints = {entry["name"]: entry for entry in metadata["endpoints"]}
    assert endpoints["primary"]["endpoint"] == "https://example.com/execute"
    assert endpoints["health"]["endpoint"] == "https://example.com/health"
    assert endpoints["agentWallet"]["endpoint"] == "0.0.1234"
    assert metadata["categories"] == ["Testing"]

    created_at = datetime.fromisoformat(metadata["createdAt"])
    updated_at = datetime.fromisoformat(metadata["updatedAt"])
    assert created_at <= updated_at


def test_save_agent_metadata_locally(tmp_path, monkeypatch):
    metadata = {"agentId": "foo", "name": "Foo Agent"}

    target_dir = tmp_path / "agent_metadata"
    monkeypatch.setattr(
        "shared.metadata.publisher.METADATA_DIR",
        target_dir,
        raising=False,
    )

    path = save_agent_metadata_locally("foo", metadata)

    assert path.exists()
    assert path.parent == target_dir
    data = json.loads(path.read_text())
    assert data["agentId"] == "foo"
