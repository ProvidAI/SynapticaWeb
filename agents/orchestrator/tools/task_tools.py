"""Task management tools for Orchestrator."""

from typing import Dict, Any, Optional
import uuid
from datetime import datetime

from shared.database import SessionLocal, Task
from shared.database.models import TaskStatus


async def create_task(
    title: str,
    description: str,
    created_by: str = "orchestrator",
    metadata: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    """
    Create a new task in the system.

    Args:
        title: Task title
        description: Detailed task description
        created_by: Agent ID creating the task
        metadata: Optional metadata

    Returns:
        Created task information
    """
    db = SessionLocal()
    try:
        task_id = str(uuid.uuid4())
        task = Task(
            id=task_id,
            title=title,
            description=description,
            status=TaskStatus.PENDING,
            created_by=created_by,
            metadata=metadata or {},
        )

        db.add(task)
        db.commit()
        db.refresh(task)

        return {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "created_at": task.created_at.isoformat(),
        }
    finally:
        db.close()


async def update_task_status(
    task_id: str, status: str, result: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """
    Update task status.

    Args:
        task_id: Task ID to update
        status: New status (pending, assigned, in_progress, completed, failed)
        result: Optional result data for completed tasks

    Returns:
        Updated task information
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        task.status = TaskStatus(status)
        task.updated_at = datetime.utcnow()

        if result:
            task.result = result

        if status == "completed":
            task.completed_at = datetime.utcnow()

        db.commit()
        db.refresh(task)

        return {
            "task_id": task.id,
            "status": task.status.value,
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
        }
    finally:
        db.close()


async def get_task(task_id: str) -> Dict[str, Any]:
    """
    Get task information.

    Args:
        task_id: Task ID

    Returns:
        Task information
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        return {
            "task_id": task.id,
            "title": task.title,
            "description": task.description,
            "status": task.status.value,
            "created_by": task.created_by,
            "assigned_to": task.assigned_to,
            "created_at": task.created_at.isoformat(),
            "updated_at": task.updated_at.isoformat(),
            "completed_at": task.completed_at.isoformat() if task.completed_at else None,
            "result": task.result,
            "metadata": task.meta,
        }
    finally:
        db.close()
