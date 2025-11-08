"""TODO management tools for Orchestrator."""

from typing import List, Dict, Any, Optional

from strands import tool
from shared.task_progress import update_progress

@tool
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
            # Task might not be in database yet (in-memory only), so just send progress update
            pass
        else:
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

        # Send progress update to frontend with TODO list
        todo_list = [
            {
                "id": f"todo_{i}",
                "status": "pending",
                **item,
            }
            for i, item in enumerate(items)
        ]

        # Mark initialization and orchestrator analysis as completed when planning finishes
        update_progress(task_id, "initialization", "completed", {
            "message": "Task initialization completed"
        })

        # The initial "orchestrator running" step should complete here
        # (The final orchestrator step will complete when the entire workflow finishes)
        update_progress(task_id, "orchestrator_analysis", "completed", {
            "message": "Task analysis completed"
        })

        update_progress(task_id, "planning", "completed", {
            "message": "Created task plan with TODO list",
            "todo_list": todo_list
        })

        return {
            "task_id": task_id,
            "todo_count": len(items),
            "todo_list": todo_list,
        }
    finally:
        db.close()

@tool
async def update_todo_item(task_id: str, todo_id: str, status: str, todo_list: Optional[List[Dict[str, str]]] = None) -> Dict[str, Any]:
    """
    Update TODO item status and emit progress update to frontend.

    CRITICAL: Call this function to mark each microtask as in_progress when starting
    and completed when finished!

    Args:
        task_id: Task ID
        todo_id: TODO item ID (e.g., "todo_0", "todo_1")
        status: New status (pending, in_progress, completed, failed)
        todo_list: Optional TODO list to use if task not in database yet

    Returns:
        Updated TODO item information

    Example Usage:
        # When starting first microtask
        update_todo_item(task_id, "todo_0", "in_progress")

        # After completing negotiation + execution for first microtask
        update_todo_item(task_id, "todo_0", "completed")

        # Start second microtask
        update_todo_item(task_id, "todo_1", "in_progress")
    """
    from shared.database import SessionLocal, Task
    import logging

    logger = logging.getLogger(__name__)

    db = SessionLocal()
    try:    
        for item in todo_list:
            if item.get("id") == todo_id:
                todo_title = item.get("title", "Unknown task")
                todo_description = item.get("description", "")
                todo_assigned_to = item.get("assigned_to", None)
                found = True
                logger.info(f"[update_todo_item] Found TODO in provided list: id={todo_id}, title={todo_title}")
                break

        if not found:
            logger.warning(f"[update_todo_item] Could not find TODO {todo_id} in database or provided list")

        # Emit progress update to frontend based on status
        if status == "in_progress":
            update_progress(task_id, f"microtask_{todo_id}", "started", {
                "message": f"Starting: {todo_title}",
                "todo_id": todo_id,
                "assigned_to": todo_assigned_to,
                "description": todo_description,
                "task_name": todo_title  # Include task name for other steps to reference
            })
        elif status == "completed":
            # Emit completion for this specific microtask
            update_progress(task_id, f"microtask_{todo_id}", "completed", {
                "message": f"✓ Completed: {todo_title}",
                "todo_id": todo_id,
                "assigned_to": todo_assigned_to,
                "description": todo_description
            })
        elif status == "failed":
            update_progress(task_id, f"microtask_{todo_id}", "failed", {
                "message": f"✗ Failed: {todo_title}",
                "todo_id": todo_id,
                "assigned_to": todo_assigned_to,
                "error": "Microtask failed"
            })

        return {
            "task_id": task_id,
            "todo_id": todo_id,
            "status": status,
            "title": todo_title,
            "message": f"TODO item '{todo_title}' marked as {status}"
        }
    finally:
        db.close()
