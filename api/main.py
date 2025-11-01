"""FastAPI main application - Orchestrator Agent Entry Point."""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from dotenv import load_dotenv

from shared.database import engine, Base, SessionLocal
from shared.database.models import A2AEvent
from .middleware import logging_middleware
from agents.orchestrator.agent import create_orchestrator_agent

# Load environment variables
load_dotenv()


# Pydantic models for API requests/responses
class TaskRequest(BaseModel):
    """Request model for creating a task."""

    description: str
    capability_requirements: Optional[str] = None
    budget_limit: Optional[float] = None
    min_reputation_score: Optional[float] = 0.7
    verification_mode: Optional[str] = "standard"


class TaskResponse(BaseModel):
    """Response model for task execution."""

    task_id: str
    status: str
    result: Optional[Dict[str, Any]] = None
    error: Optional[str] = None


class A2AEventResponse(BaseModel):
    """Response model for emitted A2A messages."""

    message_id: str
    protocol: str
    message_type: str
    from_agent: str
    to_agent: str
    thread_id: str
    timestamp: datetime
    tags: Optional[List[str]] = None
    body: Dict[str, Any]


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    # Startup: Create database tables
    Base.metadata.create_all(bind=engine)
    print("Database initialized")
    print("Orchestrator agent ready")
    yield
    # Shutdown
    print("Shutting down...")


# Create FastAPI app
app = FastAPI(
    title="ProvidAI Orchestrator",
    description="Orchestrator agent that discovers, negotiates with, and executes tasks using marketplace agents",
    version="0.1.0",
    lifespan=lifespan,
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(logging_middleware)


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ProvidAI Orchestrator",
        "version": "0.1.0",
        "description": "Orchestrator agent for discovering and coordinating marketplace agents",
        "workflow": [
            "1. Receive task request",
            "2. Use negotiator_agent to discover & pay for marketplace agents",
            "3. Use executor_agent to run tasks via dynamic tooling",
            "4. Use verifier_agent to validate results & release payments",
        ],
        "endpoints": {
            "/execute": "POST - Execute a task using marketplace agents",
            "/health": "GET - Health check",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "orchestrator"}


@app.get("/a2a/events", response_model=List[A2AEventResponse])
def list_a2a_events(limit: int = 50) -> List[A2AEventResponse]:
    """Return recent A2A events emitted by the system."""

    session = SessionLocal()
    try:
        capped_limit = max(1, min(limit, 200))
        records = (
            session.query(A2AEvent)
            .order_by(A2AEvent.timestamp.desc(), A2AEvent.id.desc())
            .limit(capped_limit)
            .all()
        )

        responses = []
        for record in records:
            responses.append(
                A2AEventResponse(
                    message_id=record.message_id,
                    protocol=record.protocol,
                    message_type=record.message_type,
                    from_agent=record.from_agent,
                    to_agent=record.to_agent,
                    thread_id=record.thread_id,
                    timestamp=record.timestamp,
                    tags=record.tags or None,
                    body=record.body or {},
                )
            )

        return responses
    finally:
        session.close()


@app.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest) -> TaskResponse:
    """
    Execute a task using the orchestrator agent.

    The orchestrator will:
    1. Analyze the task and determine required capabilities
    2. Call negotiator_agent to discover and pay for suitable marketplace agents
    3. Call executor_agent to execute the task using dynamic tools
    4. Call verifier_agent to validate results and release payments

    Args:
        request: Task request with description and optional parameters

    Returns:
        TaskResponse with task ID, status, and results
    """
    task_id = str(uuid.uuid4())

    try:
        # Create orchestrator agent
        orchestrator = create_orchestrator_agent()

        # Build the orchestrator query
        query = f"""
        Task ID: {task_id}

        User Request:
        {request.description}

        Configuration:
        - Budget Limit: {request.budget_limit or "No specific limit"}
        - Minimum Reputation Score: {request.min_reputation_score}
        - Verification Mode: {request.verification_mode}
        - Initial Capability Hint: {request.capability_requirements or "Analyze the task to determine"}

        Follow your standard workflow:

        1. ANALYSIS & PLANNING
           - Create a TODO list for this task
           - Define specific agent capabilities needed (be very specific!)

        2. DISCOVERY & NEGOTIATION
           - Use negotiator_agent with detailed capability requirements

        3. EXECUTION
           - Use executor_agent with agent metadata from negotiator

        4. VERIFICATION
           - Use verifier_agent to validate and release payment

        Provide a complete summary of all steps and results.
        """

        # Run the orchestrator agent
        result = await orchestrator.run(query)

        return TaskResponse(
            task_id=task_id,
            status="completed",
            result={
                "orchestrator_response": str(result),
                "workflow": "negotiator -> executor -> verifier",
            },
        )

    except Exception as e:
        return TaskResponse(
            task_id=task_id,
            status="failed",
            error=str(e),
        )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run("api.main:app", host=host, port=port, reload=True)
