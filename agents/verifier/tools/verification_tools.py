"""Verification tools for Verifier agent."""

from typing import Dict, Any, List
import json
from datetime import datetime

from shared.database import SessionLocal, Task
from shared.database.models import TaskStatus


async def verify_task_result(task_id: str, expected_criteria: Dict[str, Any]) -> Dict[str, Any]:
    """
    Verify task execution results against expected criteria.

    Args:
        task_id: Task ID to verify
        expected_criteria: Expected criteria dict with:
            - required_fields: List of required fields in result
            - quality_threshold: Minimum quality score (0-100)
            - max_errors: Maximum allowed errors

    Returns:
        Verification result
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        if task.status != TaskStatus.COMPLETED:
            return {
                "success": False,
                "error": f"Task not completed. Current status: {task.status.value}",
            }

        result = task.result or {}

        # Check required fields
        required_fields = expected_criteria.get("required_fields", [])
        missing_fields = [field for field in required_fields if field not in result]

        if missing_fields:
            return {
                "success": False,
                "verification": "failed",
                "reason": f"Missing required fields: {missing_fields}",
            }

        # Check quality threshold
        quality_threshold = expected_criteria.get("quality_threshold", 0)
        actual_quality = result.get("quality_score", 100)

        if actual_quality < quality_threshold:
            return {
                "success": False,
                "verification": "failed",
                "reason": f"Quality score {actual_quality} below threshold {quality_threshold}",
            }

        # Check error count
        max_errors = expected_criteria.get("max_errors", float("inf"))
        actual_errors = result.get("error_count", 0)

        if actual_errors > max_errors:
            return {
                "success": False,
                "verification": "failed",
                "reason": f"Error count {actual_errors} exceeds maximum {max_errors}",
            }

        # All checks passed
        return {
            "success": True,
            "verification": "passed",
            "task_id": task_id,
            "checks": {
                "required_fields": "passed",
                "quality_threshold": "passed",
                "error_count": "passed",
            },
        }

    finally:
        db.close()


async def validate_output_schema(output: Dict[str, Any], schema: Dict[str, Any]) -> Dict[str, Any]:
    """
    Validate output matches expected schema.

    Args:
        output: Output to validate
        schema: Expected schema dict with field types

    Returns:
        Validation result

    Example:
        schema = {
            "summary": "str",
            "insights": "list",
            "confidence": "float"
        }
    """
    # SAFETY CHECK: Ensure output is a dict, not a string
    if isinstance(output, str):
        try:
            output = json.loads(output)
        except (json.JSONDecodeError, TypeError):
            # If not JSON, wrap it in a dict
            output = {"response": output}

    errors = []

    for field, expected_type in schema.items():
        if field not in output:
            errors.append(f"Missing field: {field}")
            continue

        value = output[field]
        actual_type = type(value).__name__

        # Map Python types
        type_mapping = {
            "str": "str",
            "int": "int",
            "float": "float",
            "list": "list",
            "dict": "dict",
            "bool": "bool",
        }

        if type_mapping.get(actual_type) != expected_type:
            errors.append(
                f"Field '{field}' type mismatch: expected {expected_type}, got {actual_type}"
            )

    if errors:
        return {
            "success": False,
            "validation": "failed",
            "errors": errors,
        }

    return {
        "success": True,
        "validation": "passed",
        "message": "Output schema validated successfully",
    }


async def check_quality_metrics(
    task_id: str, metrics: Dict[str, float]
) -> Dict[str, Any]:
    """
    Check quality metrics for task results.

    Args:
        task_id: Task ID
        metrics: Quality metrics to check:
            - completeness: 0-100
            - accuracy: 0-100
            - relevance: 0-100

    Returns:
        Quality check result
    """
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()

        if not task:
            return {"success": False, "error": f"Task {task_id} not found"}

        result = task.result or {}

        # Calculate overall quality score
        scores = []
        failed_metrics = []

        for metric, threshold in metrics.items():
            actual = result.get(f"{metric}_score", 0)
            scores.append(actual)

            if actual < threshold:
                failed_metrics.append(
                    {"metric": metric, "expected": threshold, "actual": actual}
                )

        overall_score = sum(scores) / len(scores) if scores else 0

        if failed_metrics:
            return {
                "success": False,
                "quality_check": "failed",
                "overall_score": overall_score,
                "failed_metrics": failed_metrics,
            }

        return {
            "success": True,
            "quality_check": "passed",
            "overall_score": overall_score,
            "message": "All quality metrics met",
        }

    finally:
        db.close()
