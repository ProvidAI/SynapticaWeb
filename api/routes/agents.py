"""Agent management routes."""

from typing import List
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.orm import Session

from shared.database import get_db, Agent

router = APIRouter()


class AgentResponse(BaseModel):
    """Agent response."""

    agent_id: str
    name: str
    agent_type: str
    description: str
    capabilities: List[str]
    status: str

    class Config:
        from_attributes = True


class DiscoverAgentsRequest(BaseModel):
    """Discover agents request."""

    capability: str


@router.get("/{agent_id}", response_model=AgentResponse)
async def get_agent(agent_id: str, db: Session = Depends(get_db)):
    """Get agent by ID."""
    agent = db.query(Agent).filter(Agent.agent_id == agent_id).first()

    if not agent:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentResponse(
        agent_id=agent.agent_id,
        name=agent.name,
        agent_type=agent.agent_type,
        description=agent.description,
        capabilities=agent.capabilities or [],
        status=agent.status,
    )


@router.get("/", response_model=List[AgentResponse])
async def list_agents(db: Session = Depends(get_db)):
    """List all agents."""
    agents = db.query(Agent).all()

    return [
        AgentResponse(
            agent_id=agent.agent_id,
            name=agent.name,
            agent_type=agent.agent_type,
            description=agent.description,
            capabilities=agent.capabilities or [],
            status=agent.status,
        )
        for agent in agents
    ]


@router.post("/discover")
async def discover_agents(request: DiscoverAgentsRequest):
    """Discover marketplace agents by capability using ERC-8004."""
    from agents.negotiator import create_negotiator_agent

    agent = create_negotiator_agent()

    prompt = f"Discover agents with capability: {request.capability}"
    result = await agent.run(prompt)

    return {"capability": request.capability, "result": result}
