"""FastAPI main application - Orchestrator Agent Entry Point."""

import os
import uuid
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

from dotenv import load_dotenv
from fastapi import BackgroundTasks, FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import shared.task_progress as task_progress
from agents.orchestrator.agent import create_orchestrator_agent
from shared.database import Base, SessionLocal, engine
from shared.database.models import A2AEvent

from .middleware import logging_middleware
from .routes import agents as agents_routes

# Load environment variables
load_dotenv()

# In-memory task storage for progress tracking
tasks_storage: Dict[str, Dict[str, Any]] = {}


def update_task_progress(task_id: str, step: str, status: str, data: Optional[Dict] = None):
    """Update task progress for frontend polling."""
    if task_id not in tasks_storage:
        tasks_storage[task_id] = {
            "task_id": task_id,
            "status": "processing",
            "progress": [],
            "current_step": step
        }

    if "progress" not in tasks_storage[task_id]:
        tasks_storage[task_id]["progress"] = []

    tasks_storage[task_id]["progress"].append({
        "step": step,
        "status": status,
        "timestamp": datetime.utcnow().isoformat(),
        "data": data or {}
    })

    tasks_storage[task_id]["current_step"] = step

    # Only update overall task status when orchestrator completes/fails
    # Intermediate steps (planning, negotiator, executor) shouldn't affect overall status
    if step == "orchestrator" and status in ["completed", "failed"]:
        tasks_storage[task_id]["status"] = status
    elif tasks_storage[task_id]["status"] not in ["completed", "failed"]:
        # Keep as "processing" for all intermediate steps
        tasks_storage[task_id]["status"] = "processing"


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
    # Register progress callback for task updates
    task_progress.set_progress_callback(update_task_progress)
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
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add custom middleware
app.middleware("http")(logging_middleware)

# Include routers
app.include_router(agents_routes.router, prefix="/api/agents", tags=["agents"])


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "ProvidAI Orchestrator",
        "version": "0.1.0",
        "description": "Orchestrator agent for discovering and coordinating marketplace agents",
        "workflow": [
            "1. Analyze request and decompose into specialized microtasks",
            "2. For each microtask: discover agents (negotiator) → authorize payment → execute task",
            "3. Aggregate results from all microtasks",
            "4. Return complete output",
        ],
        "endpoints": {
            "/execute": "POST - Execute a task using marketplace agents",
            "/health": "GET - Health check",
            "/api/tasks/{task_id}": "GET - Poll task status and progress",
            "/api/tasks/history": "GET - Retrieve task history with payments",
            "/a2a/events": "GET - View A2A message events",
        },
    }


@app.get("/health")
async def health():
    """Health check endpoint."""
    return {"status": "healthy", "agent": "orchestrator"}


class SubTaskResponse(BaseModel):
    """Response model for subtask (payment) details."""
    id: str
    description: str
    agent_used: str
    agent_reputation: float
    cost: float
    status: str
    timestamp: datetime


class TaskHistoryResponse(BaseModel):
    """Response model for task history."""
    id: str
    research_query: str
    total_cost: float
    status: str
    created_at: datetime
    sub_tasks: List[SubTaskResponse]


@app.get("/api/tasks/history", response_model=List[TaskHistoryResponse])
def get_task_history(limit: int = 50) -> List[TaskHistoryResponse]:
    """
    Retrieve task history with associated payments (microtransactions).

    Returns tasks ordered by creation date (newest first) with their
    associated payment details representing agent microtransactions.
    """
    from shared.database.models import Agent, Payment, Task

    session = SessionLocal()
    try:
        capped_limit = max(1, min(limit, 200))

        # Query tasks with their payments
        tasks = (
            session.query(Task)
            .order_by(Task.created_at.desc())
            .limit(capped_limit)
            .all()
        )

        responses = []
        for task in tasks:
            # Get all payments for this task
            payments = (
                session.query(Payment)
                .filter(Payment.task_id == task.id)
                .order_by(Payment.created_at.asc())
                .all()
            )

            # Build subtasks from payments
            sub_tasks = []
            total_cost = 0.0

            for payment in payments:
                # Get agent details
                agent = session.query(Agent).filter(Agent.agent_id == payment.to_agent_id).first()
                agent_name = agent.name if agent else payment.to_agent_id

                # Get agent reputation (default to 0.0 if not found)
                from shared.database.models import AgentReputation
                reputation_record = session.query(AgentReputation).filter(
                    AgentReputation.agent_id == payment.to_agent_id
                ).first()
                reputation_score = reputation_record.reputation_score if reputation_record else 0.0

                # Extract description from payment metadata
                description = "Agent task execution"
                if payment.meta and isinstance(payment.meta, dict):
                    description = payment.meta.get("description", description)

                sub_tasks.append(SubTaskResponse(
                    id=payment.id,
                    description=description,
                    agent_used=agent_name,
                    agent_reputation=reputation_score,
                    cost=payment.amount,
                    status=payment.status.value,
                    timestamp=payment.created_at
                ))

                total_cost += payment.amount

            # Map task status to frontend format
            status_mapping = {
                "pending": "in_progress",
                "assigned": "in_progress",
                "in_progress": "in_progress",
                "completed": "completed",
                "failed": "failed"
            }
            frontend_status = status_mapping.get(task.status.value, "in_progress")

            responses.append(TaskHistoryResponse(
                id=task.id,
                research_query=task.title or task.description or "Unknown task",
                total_cost=total_cost,
                status=frontend_status,
                created_at=task.created_at,
                sub_tasks=sub_tasks
            ))

        return responses
    finally:
        session.close()


@app.get("/api/tasks/{task_id}")
async def get_task_status(task_id: str):
    """Get task status and progress for frontend polling."""
    if task_id not in tasks_storage:
        return {
            "task_id": task_id,
            "status": "not_found",
            "error": "Task not found"
        }

    return tasks_storage[task_id]


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


async def run_orchestrator_task(task_id: str, request: TaskRequest):
    """Background task to run the orchestrator agent."""
    import logging
    logger = logging.getLogger(__name__)

    try:
        # Create Task record in database for transaction history
        from datetime import datetime

        from shared.database import SessionLocal
        from shared.database.models import Task

        db = SessionLocal()
        try:
            task = Task(
                id=task_id,
                title=f"Research: {request.description[:50]}...",
                description=request.description,
                status="in_progress",
                created_at=datetime.utcnow(),
                meta={
                    "budget_limit": request.budget_limit,
                    "min_reputation_score": request.min_reputation_score,
                    "verification_mode": request.verification_mode,
                    "capability_requirements": request.capability_requirements,
                }
            )
            db.add(task)
            db.commit()
            logger.info(f"Created Task record in database: {task_id}")
        finally:
            db.close()

        # Update progress - initialization
        update_task_progress(task_id, "initialization", "started", {
            "message": "Starting task execution",
            "description": request.description
        })

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

        Execute your standard workflow to completion. Remember to:
        - Break complex requests into specialized microtasks when beneficial
        - Define specific, detailed capability requirements for each agent
        - Actually call all agent tools (negotiator, authorize_payment, executor)
        - Aggregate results and return a complete summary
        """

        # Run the orchestrator agent
        update_task_progress(task_id, "orchestrator_analysis", "running", {
            "message": "Orchestrator analyzing task and coordinating agents"
        })

        result = await orchestrator.run(query)

        # Log the full orchestrator response
        logger.info("========== ORCHESTRATOR RESPONSE START ==========")
        logger.info(f"{result}")
        logger.info("========== ORCHESTRATOR RESPONSE END ==========")

        # Update final status
        update_task_progress(task_id, "orchestrator", "completed", {
            "message": "Generated research output successfully",
            "result": str(result)
        })

        tasks_storage[task_id]["status"] = "completed"
        tasks_storage[task_id]["result"] = {
            "orchestrator_response": str(result),
            "workflow": "Task decomposition → Per microtask: (negotiator → authorize → executor) → Aggregation",
        }

        # Update Task status in database
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "completed"
                db.commit()
                logger.info(f"Updated Task status to completed: {task_id}")
        finally:
            db.close()

    except Exception as e:
        # Update error status
        logger.error(f"Task {task_id} failed: {e}", exc_info=True)
        update_task_progress(task_id, "orchestrator", "failed", {
            "error": str(e)
        })

        tasks_storage[task_id]["status"] = "failed"
        tasks_storage[task_id]["error"] = str(e)

        # Update Task status in database
        db = SessionLocal()
        try:
            task = db.query(Task).filter(Task.id == task_id).first()
            if task:
                task.status = "failed"
                db.commit()
                logger.info(f"Updated Task status to failed: {task_id}")
        finally:
            db.close()


@app.post("/execute", response_model=TaskResponse)
async def execute_task(request: TaskRequest, background_tasks: BackgroundTasks) -> TaskResponse:
    """
    Execute a task using the orchestrator agent.

    The orchestrator will:
    1. Decompose the task into specialized microtasks
    2. For each microtask: discover agents → authorize payment → execute
    3. Aggregate results from all microtasks
    4. Return complete output

    Args:
        request: Task request with description and optional parameters

    Returns:
        TaskResponse with task ID - execution happens in background
    """
    task_id = str(uuid.uuid4())

    # Initialize task in storage
    tasks_storage[task_id] = {
        "task_id": task_id,
        "status": "processing",
        "progress": [],
        "current_step": "initializing"
    }

    # Run orchestrator in background
    background_tasks.add_task(run_orchestrator_task, task_id, request)

    # Return immediately with task_id
    return TaskResponse(
        task_id=task_id,
        status="processing",
        result={
            "message": "Task started, poll /api/tasks/{task_id} for progress"
        }
    )


if __name__ == "__main__":
    import uvicorn

    host = os.getenv("API_HOST", "0.0.0.0")
    port = int(os.getenv("API_PORT", "8000"))

    uvicorn.run("api.main:app", host=host, port=port, reload=True)
