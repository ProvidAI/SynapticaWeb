"""Meta-tooling capabilities for Executor agent."""

import os
import importlib.util
from typing import Dict, Any, List
from pathlib import Path
from datetime import datetime

from shared.database import SessionLocal, DynamicTool


DYNAMIC_TOOLS_DIR = Path(__file__).parent.parent / "dynamic_tools"
DYNAMIC_TOOLS_DIR.mkdir(exist_ok=True)


async def create_dynamic_tool(
    task_id: str,
    tool_name: str,
    agent_metadata: Dict[str, Any],
    tool_spec: Dict[str, Any],
) -> Dict[str, Any]:
    """
    Create a dynamic tool for integrating with a discovered marketplace agent.

    This is the KEY meta-tooling function that generates Python code at runtime.

    Args:
        task_id: Associated task ID
        tool_name: Name for the new tool (e.g., "call_data_analyzer")
        agent_metadata: Metadata from ERC-8004 discovery
        tool_spec: Tool specification with:
            - endpoint: API endpoint URL
            - method: HTTP method (GET, POST, etc.)
            - parameters: List of parameter specs [{"name": "...", "type": "...", "description": "..."}]
            - auth_type: Authentication type (bearer, api_key, none)
            - description: Tool description

    Returns:
        Created tool information

    Example:
        tool = await create_dynamic_tool(
            task_id="task-123",
            tool_name="analyze_sales_data",
            agent_metadata={"agent_id": "agent-456", "name": "Data Analyzer"},
            tool_spec={
                "endpoint": "https://analyzer.example.com/api/analyze",
                "method": "POST",
                "parameters": [
                    {"name": "data", "type": "str", "description": "CSV data to analyze"},
                    {"name": "analysis_type", "type": "str", "description": "Type of analysis"}
                ],
                "auth_type": "bearer",
                "description": "Analyze sales data and generate insights"
            }
        )
    """
    # Generate Python code for the tool
    tool_code = _generate_tool_code(tool_name, tool_spec, agent_metadata)

    # Save to file
    file_path = DYNAMIC_TOOLS_DIR / f"{tool_name}.py"
    file_path.write_text(tool_code)

    # Save to database
    db = SessionLocal()
    try:
        dynamic_tool = DynamicTool(
            task_id=task_id,
            tool_name=tool_name,
            tool_description=tool_spec.get("description", ""),
            tool_code=tool_code,
            file_path=str(file_path),
            meta={
                "agent_metadata": agent_metadata,
                "tool_spec": tool_spec,
                "created_at": datetime.utcnow().isoformat(),
            },
        )

        db.add(dynamic_tool)
        db.commit()
        db.refresh(dynamic_tool)

        return {
            "tool_id": dynamic_tool.id,
            "tool_name": tool_name,
            "file_path": str(file_path),
            "description": tool_spec.get("description", ""),
            "status": "created",
            "message": f"Dynamic tool '{tool_name}' created successfully. Use load_and_execute_tool to run it.",
        }
    finally:
        db.close()


def _generate_tool_code(
    tool_name: str, tool_spec: Dict[str, Any], agent_metadata: Dict[str, Any]
) -> str:
    """Generate Python code for a dynamic tool."""
    endpoint = tool_spec.get("endpoint", "")
    method = tool_spec.get("method", "POST").lower()
    parameters = tool_spec.get("parameters", [])
    auth_type = tool_spec.get("auth_type", "none")
    description = tool_spec.get("description", "")

    # Build function parameters
    param_list = []
    param_docs = []
    for param in parameters:
        param_name = param["name"]
        param_type = param["type"]
        param_desc = param.get("description", "")
        param_list.append(f'{param_name}: {param_type}')
        param_docs.append(f'        {param_name}: {param_desc}')

    # Add auth parameter if needed
    if auth_type != "none":
        param_list.append("api_key: str = None")
        param_docs.append("        api_key: Authentication key")

    params_str = ", ".join(param_list)
    params_doc_str = "\n".join(param_docs)

    # Build request body
    request_params = {param["name"]: f'{{{param["name"]}}}' for param in parameters}
    request_body = str(request_params).replace("'", '"')

    # Build headers
    if auth_type == "bearer":
        headers_code = '''headers={"Authorization": f"Bearer {api_key}"} if api_key else {},'''
    elif auth_type == "api_key":
        headers_code = '''headers={"X-API-Key": api_key} if api_key else {},'''
    else:
        headers_code = ""

    # Generate code
    code = f'''"""
Dynamically generated tool for {agent_metadata.get("name", "agent")}.
Generated at: {datetime.utcnow().isoformat()}
Agent: {agent_metadata.get("agent_id", "unknown")}
"""

import httpx
from typing import Dict, Any


async def {tool_name}({params_str}) -> Dict[str, Any]:
    """
    {description}

    Args:
{params_doc_str}

    Returns:
        Dict with API response
    """
    endpoint = "{endpoint}"

    # Prepare request data
    request_data = {request_body}

    # Make API call
    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.{method}(
                endpoint,
                json=request_data,
                {headers_code}
            )
            response.raise_for_status()
            return {{
                "success": True,
                "data": response.json(),
                "status_code": response.status_code
            }}
        except httpx.HTTPError as e:
            return {{
                "success": False,
                "error": str(e),
                "status_code": getattr(e.response, "status_code", None) if hasattr(e, "response") else None
            }}
        except Exception as e:
            return {{
                "success": False,
                "error": f"Unexpected error: {{str(e)}}"
            }}
'''

    return code


async def load_and_execute_tool(
    tool_name: str, parameters: Dict[str, Any]
) -> Dict[str, Any]:
    """
    Load a dynamically created tool and execute it.

    This demonstrates the meta-tooling pattern: loading runtime-generated code.

    Args:
        tool_name: Name of the tool to load
        parameters: Parameters to pass to the tool

    Returns:
        Tool execution result

    Example:
        result = await load_and_execute_tool(
            tool_name="analyze_sales_data",
            parameters={"data": "...", "analysis_type": "trends", "api_key": "..."}
        )
    """
    # Get tool from database
    db = SessionLocal()
    try:
        tool = db.query(DynamicTool).filter(DynamicTool.tool_name == tool_name).first()

        if not tool:
            return {"success": False, "error": f"Tool '{tool_name}' not found"}

        file_path = tool.file_path

        # Load the module dynamically
        spec = importlib.util.spec_from_file_location(tool_name, file_path)
        if spec is None or spec.loader is None:
            return {"success": False, "error": f"Could not load tool from {file_path}"}

        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        # Get the tool function
        tool_func = getattr(module, tool_name)

        # Execute the tool
        result = await tool_func(**parameters)

        # Update usage count
        tool.used_count += 1
        db.commit()

        return {
            "success": True,
            "tool_name": tool_name,
            "result": result,
            "usage_count": tool.used_count,
        }

    except Exception as e:
        return {"success": False, "error": f"Error executing tool: {str(e)}"}
    finally:
        db.close()


async def list_dynamic_tools(task_id: str = None) -> Dict[str, Any]:
    """
    List all available dynamic tools.

    Args:
        task_id: Optional task ID to filter tools

    Returns:
        List of dynamic tools
    """
    db = SessionLocal()
    try:
        query = db.query(DynamicTool)

        if task_id:
            query = query.filter(DynamicTool.task_id == task_id)

        tools = query.all()

        return {
            "total_tools": len(tools),
            "tools": [
                {
                    "tool_id": tool.id,
                    "tool_name": tool.tool_name,
                    "description": tool.tool_description,
                    "task_id": tool.task_id,
                    "created_at": tool.created_at.isoformat(),
                    "used_count": tool.used_count,
                }
                for tool in tools
            ],
        }
    finally:
        db.close()
