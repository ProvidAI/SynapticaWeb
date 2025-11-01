"""Task progress tracking for updating frontend status."""

from datetime import datetime
from typing import Dict, Any, Optional, Callable

_progress_callback: Optional[Callable] = None


def set_progress_callback(callback: Callable):
    """Set the global progress callback function.

    Args:
        callback: Function that takes (task_id, step, status, data) and updates task progress
    """
    global _progress_callback
    _progress_callback = callback


def update_progress(task_id: str, step: str, status: str, data: Optional[Dict] = None):
    """Update task progress if a callback is registered.

    Args:
        task_id: Task ID
        step: Current step name (e.g., "negotiator", "executor", "verifier")
        status: Status of the step (e.g., "started", "completed", "failed")
        data: Optional additional data to include in progress update
    """
    if _progress_callback:
        _progress_callback(task_id, step, status, data)
