"""TODO management tools for Orchestrator."""

from typing import List, Dict, Any


async def create_todo_list(task_id: str, items: List[Dict[str, str]]) -> Dict[str, Any]:
    """
    Create a structured TODO list for a task.

    Args:
        task_id: Task ID
        items: List of TODO items, each with 'title', 'description', 'assigned_to'

    Returns:
        Created TODO list information

    Example:
        items = [
            {
                "title": "Discover marketplace agents",
                "description": "Use ERC-8004 to find agents with 'data-analysis' capability",
                "assigned_to": "negotiator"
            },
            {
                "title": "Create custom integration tool",
                "description": "Generate dynamic tool for discovered agent API",
                "assigned_to": "executor"
            }
        ]
    """
    from shared.database import SessionLocal, Task

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        # Store TODO list in task metadata
        if task.meta is None:
            task.meta = {}

        task.meta["todo_list"] = [
            {
                "id": f"todo_{i}",
                "status": "pending",
                **item,
            }
            for i, item in enumerate(items)
        ]

        db.commit()
        db.refresh(task)

        return {
            "task_id": task_id,
            "todo_count": len(items),
            "todo_list": task.meta["todo_list"],
        }
    finally:
        db.close()


async def update_todo_item(task_id: str, todo_id: str, status: str) -> Dict[str, Any]:
    """
    Update TODO item status.

    Args:
        task_id: Task ID
        todo_id: TODO item ID
        status: New status (pending, in_progress, completed)

    Returns:
        Updated TODO item information
    """
    from shared.database import SessionLocal, Task

    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if not task:
            raise ValueError(f"Task {task_id} not found")

        if not task.meta or "todo_list" not in task.meta:
            raise ValueError(f"No TODO list found for task {task_id}")

        # Update TODO item
        for item in task.meta["todo_list"]:
            if item["id"] == todo_id:
                item["status"] = status
                break
        else:
            raise ValueError(f"TODO item {todo_id} not found")

        # Mark modified for SQLAlchemy
        task.meta = dict(task.meta)
        db.commit()
        db.refresh(task)

        return {
            "task_id": task_id,
            "todo_id": todo_id,
            "status": status,
        }
    finally:
        db.close()
