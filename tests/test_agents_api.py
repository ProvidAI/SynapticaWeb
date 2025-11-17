from unittest.mock import AsyncMock

import pytest
from fastapi.testclient import TestClient

from api.main import app
from shared.database import Agent as AgentModel, AgentReputation, SessionLocal
from shared.metadata.publisher import PinataUploadResult


def _clear_agents():
    session = SessionLocal()
    try:
        session.query(AgentReputation).delete()
        session.query(AgentModel).delete()
        session.commit()
    finally:
        session.close()


@pytest.fixture
def client(monkeypatch):
    _clear_agents()

    monkeypatch.setattr("api.routes.agents.ensure_registry_cache", lambda force=False: None)
    monkeypatch.setattr("api.routes.agents.get_registry_sync_status", lambda: ("test", None))

    mock_publish = AsyncMock(
        return_value=PinataUploadResult(
            cid="bafy-test",
            ipfs_uri="ipfs://bafy-test",
            gateway_url="https://gateway.pinata.cloud/ipfs/bafy-test",
            pinata_url="https://app.pinata.cloud/pinmanager?search=bafy-test",
        )
    )
    monkeypatch.setattr("api.routes.agents.publish_agent_metadata", mock_publish)
    return TestClient(app)


def _sample_payload():
    return {
        "agent_id": "test-agent",
        "name": "Test Agent",
        "description": "Performs useful tests for integration.",
        "capabilities": ["testing", "validation"],
        "categories": ["Quality"],
        "endpoint_url": "https://example.com/agents/test",
        "base_rate": 1.5,
        "currency": "HBAR",
        "rate_type": "per_task",
        "contact_email": "qa@example.com",
    }


def test_register_agent_creates_record(client: TestClient):
    response = client.post("/api/agents", json=_sample_payload())
    assert response.status_code == 201

    data = response.json()
    assert data["agent_id"] == "test-agent"
    assert data["pricing"]["rate"] == 1.5
    assert data["metadata_cid"] == "bafy-test"
    assert data["erc8004_metadata_uri"] == "ipfs://bafy-test"
    assert data["reputation_score"] == 0.5
    assert "operator_checklist" in data

    session = SessionLocal()
    try:
        agent = session.query(AgentModel).filter(AgentModel.agent_id == "test-agent").one()
        assert agent.meta["metadata_cid"] == "bafy-test"
        assert agent.erc8004_metadata_uri == "ipfs://bafy-test"
    finally:
        session.close()


def test_duplicate_agent_id_returns_conflict(client: TestClient):
    payload = _sample_payload()
    assert client.post("/api/agents", json=payload).status_code == 201
    conflict = client.post("/api/agents", json=payload)
    assert conflict.status_code == 409
    assert conflict.json()["detail"].startswith("Agent 'test-agent' already exists")


def test_list_agents_returns_created_agent(client: TestClient):
    client.post("/api/agents", json=_sample_payload())
    listing = client.get("/api/agents")
    assert listing.status_code == 200
    data = listing.json()
    assert data["sync_status"] == "test"
    assert data["total"] == 1
    assert data["agents"][0]["agent_id"] == "test-agent"
    assert data["agents"][0]["pricing"]["rate"] == 1.5
    assert data["agents"][0]["reputation_score"] == 0.5
